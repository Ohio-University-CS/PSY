from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum, Count, Min, Max
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.authentication import TokenAuthentication

from datetime import date

import random
from .models import CanBetUser, Item, InventoryEntry, CrateOpen, ShopPurchase, Lootbox, LootboxInventoryEntry, CanvasSubmission
from .services import open_loot_box


# ═══════════════════════════════════════════════════════════════════════════════
#  PAGE VIEWS

def home(request):
    return render(request, 'home.html')

def about(request):
    return render(request, 'about.html')

def privacy(request):
    return render(request, 'privacy.html')

def login_view(request):
    if request.user.is_authenticated:
        return redirect('main')
    if request.method == 'POST':
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is None:
            try:
                matched = CanBetUser.objects.get(email=email)
                user = authenticate(request, username=matched.username, password=password)
            except CanBetUser.DoesNotExist:
                user = None
        if user:
            login(request, user)
            return redirect('main')
        return render(request, 'login.html', {'error': 'Invalid email or password.'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('login')

@login_required
def main(request):
    user  = request.user
    top5  = CanBetUser.objects.order_by('-bit_balance')[:5]
    opens = list(user.crate_opens.select_related('item_won')[:5])
    buys  = list(user.purchases.select_related('item')[:5])
    recent = sorted(
        opens + buys,
        key=lambda x: getattr(x, 'opened_at', None) or getattr(x, 'purchased_at', None),
        reverse=True
    )[:5]
    return render(request, 'main.html', {
        'user': user, 'top5': top5, 'recent_activity': recent,
    })

@login_required
def inventory(request):
    entries = request.user.inventory.select_related('item').order_by('item__collection', 'item__rarity', 'item__name')
    return render(request, 'inventory.html', {'entries': entries})

@login_required
def leaderboard(request):
    sort = request.GET.get('sort', 'bits')
    page = int(request.GET.get('page', 1))
    per_page = 10

    qs = CanBetUser.objects.annotate(
        crate_count=Count('crate_opens', distinct=True),
        best_rarity=Min('inventory__item__rarity'),
        rarity_achieved=Min('inventory__obtained_at'),
        last_crate=Max('crate_opens__opened_at'),
    )

    if sort == 'rarity':
        qs = qs.order_by('best_rarity', 'rarity_achieved')
    elif sort == 'crates':
        qs = qs.order_by('-crate_count', 'last_crate')
    else:
        qs = qs.order_by('-bit_balance')

    total = qs.count()
    total_pages = max(1, (total + per_page - 1) // per_page)
    entries = qs[(page - 1) * per_page : page * per_page]

    results = []
    for i, u in enumerate(entries):
        rank = (page - 1) * per_page + i + 1
        results.append({
            'rank': rank,
            'username': u.username,
            'bits': u.bit_balance,
            'crates': u.crate_count,
            'is_you': request.user.is_authenticated and u.pk == request.user.pk,
        })

    return render(request, 'leaderboard.html', {
        'entries': results,
        'sort': sort,
        'page': page,
        'total_pages': total_pages,
    })

@login_required
def profile(request):
    user = request.user
    RARITY_ORDER = {'LEGENDARY': 0, 'EPIC': 1, 'RARE': 2, 'COMMON': 3}
    entries = list(user.inventory.select_related('item'))
    entries.sort(key=lambda e: RARITY_ORDER.get(e.item.rarity, 99))
    best_pulls  = entries[:5]
    best_pull   = entries[0].item.name if entries else None
    total_spent = user.purchases.aggregate(total=Sum('bits_spent'))['total'] or 0
    return render(request, 'profile.html', {
        'user': user, 'best_pulls': best_pulls,
        'best_pull': best_pull, 'total_spent': total_spent,
    })

@login_required
def settings_view(request):
    return render(request, 'settings.html')

@login_required
def shop(request):
    items = Item.objects.filter(shop_price__gt=0).order_by('collection', 'shop_price', 'name')
    owned_ids = set(request.user.inventory.values_list('item_id', flat=True))
    daily_items = get_daily_shop_items()

    return render(request, 'shop.html', {
        'items': items,
        'owned_ids': owned_ids,
        'daily_items': daily_items,
    })

@login_required
def crate(request):
    return render(request, 'crate.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        user.delete()
        return redirect('home')
    return redirect('settings')


def register_view(request):
    if request.user.is_authenticated:
        return redirect('main')
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm  = request.POST.get('confirm', '')
        if password != confirm:
            return render(request, 'register.html', {'error': 'Passwords do not match.', 'username': username, 'email': email})
        if CanBetUser.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already taken.', 'email': email})
        if CanBetUser.objects.filter(email=email).exists():
            return render(request, 'register.html', {'error': 'Email already registered.', 'username': username})
        user = CanBetUser.objects.create_user(username=username, email=email, password=password)
        login(request, user)
        return redirect('main')
    return render(request, 'register.html')


# ═══════════════════════════════════════════════════════════════════════════════
#  REST API

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_me(request):
    u = request.user
    return Response({
        'username': u.username, 'bit_balance': u.bit_balance,
        'crates_opened': u.crates_opened, 'rank': u.rank,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_open_crate(request):
    crate_type = request.data.get('crate_type', '').upper()
    user = request.user

    try:
        lootbox = Lootbox.objects.get(crate_type=crate_type, is_active=True)
    except Lootbox.DoesNotExist:
        return Response({'error': 'Crate type not found.'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        won_item = open_loot_box(user, lootbox)
    except LootboxInventoryEntry.DoesNotExist:
        return Response({'error': "You don't have this crate."}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    user.refresh_from_db()

    return Response({
        'item': {
            'name': won_item.name,
            'rarity': won_item.rarity,
            'sprite_path': won_item.sprite_path,
        },
        'new_balance': user.bit_balance,
        'crates_opened': user.crates_opened,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_buy_item(request):
    item = get_object_or_404(Item, pk=request.data.get('item_id'))
    user = request.user
    if item.shop_price <= 0:
        return Response({'error': 'Item not for sale.'}, status=status.HTTP_400_BAD_REQUEST)
    if user.bit_balance < item.shop_price:
        return Response({'error': 'Not enough Bits.'}, status=status.HTTP_402_PAYMENT_REQUIRED)
    if InventoryEntry.objects.filter(user=user, item=item).exists():
        return Response({'error': 'Already owned.'}, status=status.HTTP_409_CONFLICT)
    with transaction.atomic():
        user.bit_balance -= item.shop_price
        user.save(update_fields=['bit_balance'])
        InventoryEntry.objects.create(user=user, item=item)
        ShopPurchase.objects.create(user=user, item=item, bits_spent=item.shop_price)
    return Response({'new_balance': user.bit_balance})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_inventory(request):
    return Response([
        {'item_id': e.item.id, 'name': e.item.name, 'rarity': e.item.rarity,
         'sprite_path': e.item.sprite_path, 'quantity': e.quantity}
        for e in request.user.inventory.select_related('item')
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def api_leaderboard(request):
    return Response([
        {'rank': idx+1, 'username': p.username, 'bit_balance': p.bit_balance, 'crates_opened': p.crates_opened}
        for idx, p in enumerate(CanBetUser.objects.order_by('-bit_balance')[:50])
    ])


@api_view(['GET'])
@permission_classes([AllowAny])
def api_recent_opens(request):
    opens = CrateOpen.objects.select_related('user', 'item_won').order_by('-opened_at')[:50]
    return Response([
        {
            'id':          o.id,
            'username':    o.user.username,
            'item':        o.item_won.name if o.item_won else '?',
            'rarity':      o.item_won.rarity if o.item_won else '?',
            'sprite_path': o.item_won.sprite_path if o.item_won else '',
            'opened_at':   o.opened_at.isoformat(),
        }
        for o in opens
    ])


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_buy_lootbox(request):
    lootbox_id = request.data.get('lootbox_id')
    lootbox = get_object_or_404(Lootbox, pk=lootbox_id)
    user = request.user

    if not lootbox.is_active:
        return Response({'error': 'This lootbox is not available.'}, status=status.HTTP_400_BAD_REQUEST)

    if user.bit_balance < lootbox.cost_bits:
        return Response({'error': 'Not enough Bits.'}, status=status.HTTP_402_PAYMENT_REQUIRED)

    with transaction.atomic():
        user.bit_balance -= lootbox.cost_bits
        user.save(update_fields=['bit_balance'])

        entry, _ = LootboxInventoryEntry.objects.get_or_create(
            user=user, loot_box=lootbox,
            defaults={'quantity': 0}
        )
        entry.quantity += 1
        entry.save(update_fields=['quantity'])

    return Response({
        'message': f'Successfully purchased {lootbox.name}!',
        'new_balance': user.bit_balance,
        'lootbox_name': lootbox.name,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_lootboxes(request):
    lootboxes = Lootbox.objects.filter(is_active=True).values(
        'id', 'name', 'crate_type', 'cost_bits', 'sprite_path'
    )
    user_inventory = request.user.loot_box_inventory.values_list('loot_box_id', 'quantity')
    user_inventory_map = {lb_id: qty for lb_id, qty in user_inventory}

    return Response([
        {
            **lb,
            'quantity': user_inventory_map.get(lb['id'], 0)
        }
        for lb in lootboxes
    ])


# ═══════════════════════════════════════════════════════════════════════════════
#  EXTENSION AUTH API

@csrf_exempt
@api_view(['POST'])

@permission_classes([AllowAny])
def api_token_login(request):
    if request.user and request.user.is_authenticated:
        token, _ = Token.objects.get_or_create(user=request.user)
        return Response({'token': token.key, 'username': request.user.username})

    username = request.data.get('username', '').strip()
    password = request.data.get('password', '')

    user = authenticate(request, username=username, password=password)

    # Also allow login by email
    if user is None and username:
        try:
            matched = CanBetUser.objects.get(email=username)
            user = authenticate(request, username=matched.username, password=password)
        except CanBetUser.DoesNotExist:
            pass

    if user is None:
        return Response({'error': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'username': user.username})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_crate_pool(request, crate_type):
    try:
        lootbox = Lootbox.objects.get(crate_type=crate_type.upper(), is_active=True)
    except Lootbox.DoesNotExist:
        return Response({'error': 'Crate not found.'}, status=status.HTTP_404_NOT_FOUND)

    entries = lootbox.entries.select_related('item').all()
    return Response([
        {
            'name': e.item.name,
            'rarity': e.item.rarity,
            'sprite_path': e.item.sprite_path,
            'weight': e.weight,
        }
        for e in entries
    ])

# ═══════════════════════════════════════════════════════════════════════════════
#  EXTENSION SYNC API

BITS_PER_SUBMISSION = 200

@csrf_exempt
@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def api_canvas_sync(request):
    canvas_user_id = str(request.data.get('canvas_user_id', '')).strip()
    submissions    = request.data.get('submissions', [])

    if not canvas_user_id:
        return Response({'error': 'canvas_user_id is required.'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(submissions, list) or len(submissions) == 0:
        return Response({'error': 'submissions must be a non-empty list.'}, status=status.HTTP_400_BAD_REQUEST)

    user = request.user

    # Bind canvas_user_id to this account on first sync (if not already set)
    if not user.canvas_user_id:
        if CanBetUser.objects.filter(canvas_user_id=canvas_user_id).exclude(pk=user.pk).exists():
            return Response(
                {'error': 'That Canvas account is already linked to another canBet user.'},
                status=status.HTTP_409_CONFLICT
            )
        user.canvas_user_id = canvas_user_id
        user.save(update_fields=['canvas_user_id'])
    elif user.canvas_user_id != canvas_user_id:
        return Response(
            {'error': 'canvas_user_id does not match the linked Canvas account for this user.'},
            status=status.HTTP_403_FORBIDDEN
        )

    created_count = 0
    bits_awarded  = 0

    for sub in submissions:
        course_id        = str(sub.get('course_id', '')).strip()
        course_name      = str(sub.get('course_name', course_id)).strip()
        assignment_id    = str(sub.get('assignment_id', '')).strip()
        submitted_at_raw = sub.get('submitted_at')
        score            = sub.get('score')

        if not course_id or not assignment_id or not submitted_at_raw:
            continue  # skip malformed entries silently

        submitted_at = parse_datetime(submitted_at_raw)
        if submitted_at is None:
            continue  # skip unparseable timestamps

        _, created = CanvasSubmission.objects.update_or_create(
            user=user,
            course_id=course_id,
            assignment_id=assignment_id,
            defaults={
                'course_name':  course_name,
                'submitted_at': submitted_at,
                'score':        score if score is not None else None,
                'fetched_at':   timezone.now(),
            }
        )

        if created:
            created_count += 1
            bits_awarded  += BITS_PER_SUBMISSION

    if bits_awarded:
        with transaction.atomic():
            fresh = CanBetUser.objects.filter(pk=user.pk).values_list('bit_balance', flat=True)[0]
            CanBetUser.objects.filter(pk=user.pk).update(bit_balance=fresh + bits_awarded)
            user.bit_balance = fresh + bits_awarded

    return Response({
        'created':      created_count,
        'bits_awarded': bits_awarded,
        'new_balance':  user.bit_balance,
    })

def get_daily_shop_items():
    today = date.today()

    def pick(rarity):
        items = list(Item.objects.filter(rarity=rarity))
        if not items:
            return None
        random.seed(f"{today}-{rarity}")
        return random.choice(items)

    return {
        'COMMON': pick('COMMON'),
        'RARE': pick('RARE'),
        'EPIC': pick('EPIC'),
        'LEGENDARY': pick('LEGENDARY'),
    }
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_trade(request):
    rarity_map = {
        'COMMON': ('RARE', 4),
        'RARE': ('EPIC', 3),
        'EPIC': ('LEGENDARY', 3),
    }

    from_rarity = str(request.data.get('from', '')).upper()
    selections = request.data.get('selections', [])
    user = request.user

    if from_rarity not in rarity_map:
        return Response({'error': 'Invalid trade.'}, status=400)

    if not isinstance(selections, list) or not selections:
        return Response({'error': 'No items selected.'}, status=400)

    to_rarity, required = rarity_map[from_rarity]

    cleaned = []
    total_selected = 0
    seen_ids = set()

    for row in selections:
        if not isinstance(row, dict):
            continue

        try:
            item_id = int(row.get('item_id'))
            amount = int(row.get('amount'))
        except (TypeError, ValueError):
            continue

        if item_id in seen_ids or amount < 1:
            continue

        seen_ids.add(item_id)
        cleaned.append({'item_id': item_id, 'amount': amount})
        total_selected += amount

    if total_selected != required:
        return Response(
            {'error': f'Select exactly {required} {from_rarity} item copies.'},
            status=400
        )

    entries = {
        e.item_id: e
        for e in InventoryEntry.objects.select_for_update().select_related('item').filter(
            user=user,
            item_id__in=[x['item_id'] for x in cleaned],
            item__rarity=from_rarity
        )
    }

    if len(entries) != len(cleaned):
        return Response({'error': 'One or more selected items are invalid.'}, status=400)

    for row in cleaned:
        entry = entries[row['item_id']]
        if entry.quantity < row['amount']:
            return Response(
                {'error': f'Not enough copies of {entry.item.name}.'},
                status=400
            )

    reward_item = Item.objects.filter(rarity=to_rarity).order_by('?').first()
    if not reward_item:
        return Response({'error': f'No {to_rarity} items available.'}, status=400)

    with transaction.atomic():
        for row in cleaned:
            entry = entries[row['item_id']]
            entry.quantity -= row['amount']
            if entry.quantity <= 0:
                entry.delete()
            else:
                entry.save(update_fields=['quantity'])

        reward_entry, _ = InventoryEntry.objects.get_or_create(
            user=user,
            item=reward_item,
            defaults={'quantity': 0}
        )
        reward_entry.quantity += 1
        reward_entry.save(update_fields=['quantity'])

    return Response({
        'success': True,
        'item': reward_item.name,
        'rarity': reward_item.rarity,
    })