from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

import random
from .models import CanBetUser, Item, InventoryEntry, CrateOpen, ShopPurchase, Lootbox, LootboxInventoryEntry
from .services import open_loot_box
from rest_framework.permissions import IsAuthenticated, AllowAny

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
    entries = request.user.inventory.select_related('item').order_by('item__rarity', 'item__name')
    return render(request, 'inventory.html', {'entries': entries})

@login_required
def leaderboard(request):
    players = CanBetUser.objects.order_by('-bit_balance')
    return render(request, 'leaderboard.html', {'players': players, 'user': request.user})

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
    items     = Item.objects.filter(shop_price__gt=0).order_by('collection', 'shop_price')
    owned_ids = set(request.user.inventory.values_list('item_id', flat=True))
    return render(request, 'shop.html', {'items': items, 'owned_ids': owned_ids})

@login_required
def crate(request):
    return render(request, 'crate.html')


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
    
    # Find lootbox by crate_type
    try:
        lootbox = Lootbox.objects.get(crate_type=crate_type, is_active=True)
    except Lootbox.DoesNotExist:
        return Response({'error': 'Crate type not found.'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        won_item = open_loot_box(user, lootbox)
    except LootboxInventoryEntry.DoesNotExist:
        return Response({'error': 'You don\'t have this crate.'}, status=status.HTTP_400_BAD_REQUEST)
    except ValueError as e:
        return Response({'error': str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    
    return Response({
        'item': {
            'name': won_item.name,
            'rarity': won_item.rarity,
            'sprite_path': won_item.sprite_path
        },
        'new_balance': user.bit_balance
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

from .services import open_loot_box, award_loot_box
