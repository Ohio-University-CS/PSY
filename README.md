# PSY: Canbet

Canbet is a productivity lootbox system that turns coursework activity into a game economy. The project rewards students with Bits for consistent academic effort, lets them spend those Bits on crates and collectible items, and uses leaderboards to create friendly competition around progress.

Production site: [canbet.live](https://canbet.live)

## Project Description

Traditional learning platforms usually track grades and submissions, but they do not do much to make day-to-day academic effort feel engaging. Canbet adds a lightweight game layer on top of Canvas by syncing assignment submission data, awarding Bits, and letting users collect themed items through lootboxes, shops, trades, and inventory management.

The repository contains:

- A Django web application in `Canbet/`
- REST API endpoints used by the website and browser extension
- Chrome and Firefox browser extension builds in `extension/`
- Static pixel-art assets for backgrounds, crates, and item collections

## Demo Videos

- Website demo: Add link here.
- Browser extension demo: Add link here.
- Lootbox, shop, and inventory demo: Add link here.

## Features

- User registration, login, logout, profile, settings, and account deletion
- Canvas assignment sync through the browser extension and token-authenticated API
- Bit rewards for newly synced Canvas submissions
- Lootbox purchase and opening flow with weighted item drops
- Multiple item collections, including Spooky, Space, Fantasy, and Weather
- Inventory page with item quantities, rarities, and sprites
- Daily shop items and direct item purchases
- Item quicksell system for converting duplicate items back into Bits
- Item trade-up system for exchanging lower-rarity items for higher-rarity rewards
- Avatar item selection from owned inventory items
- Leaderboards sorted by account value, Bits, crates opened, and rarest item
- Recent activity feed for crate opens and shop purchases
- Public and authenticated REST API endpoints for site and extension behavior
- Chrome and Firefox extension support for Canvas/Instructure pages

## Installation

### Prerequisites

- Python 3.11 or newer
- `pip`
- PostgreSQL, or a valid `DATABASE_URL` pointing to another supported database
- Git
- Optional: Docker, if you want to run the app in a container

### Local Setup

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd PSY
   ```
2. Move into the Django project:

   ```bash
   cd Canbet
   ```
3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```
   On macOS or Linux:

   ```bash
   source .venv/bin/activate
   ```
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```
5. Create a `.env` file in `Canbet/` and configure the values needed for your environment:

   ```env
   DJANGO_SECRET_KEY=replace-this-for-local-development
   DEBUG=True
   ALLOWED_HOSTS=127.0.0.1,localhost
   DATABASE_URL=postgresql://USER:PASSWORD@localhost:5432/CanbetBackend
   CANVAS_DOMAIN=https://ohio.instructure.com
   CANVAS_TOKEN=
   ```
6. Apply database migrations:

   ```bash
   python manage.py migrate
   ```
7. Optional: create an admin user:

   ```bash
   python manage.py createsuperuser
   ```
## How to Run

### Run the Django App Locally

From the `Canbet/` directory:

```bash
python manage.py runserver
```

Then open:

```text
http://127.0.0.1:8000/
```

### Run with Docker

From the repository root:

```bash
docker build -t canbet .
docker run --env-file Canbet/.env -p 8000:8000 canbet
```

Then open:

```text
http://127.0.0.1:8000/
```

### Run Tests

From the `Canbet/` directory:

```bash
python manage.py test
```

### Browser Extension

The extension source is split into:

- `extension/chrome/`
- `extension/firefox/`

Firefox listing:

- [addons.mozilla.org/en-US/firefox/addon/canbet/](https://addons.mozilla.org/en-US/firefox/addon/canbet/)

Chrome status:

- Awaiting approval.

For local browser testing, load the matching extension folder as an unpacked/developer extension and sign in to Canbet from the popup.

## Usage Examples

### Website Flow

1. Register or log in to a Canbet account.
2. View the main dashboard to see your Bit balance, rank, and recent activity.
3. Open the shop to buy daily items or lootboxes.
4. Open crates to receive random collectible items.
5. Visit the inventory to view owned items, set an avatar item, quicksell extras, or trade items up.
6. Check the leaderboard to compare account value, Bits, crates opened, and rarest items with other users.

### Canvas Sync Flow

1. Install the browser extension.
2. Log in to Canbet from the extension popup.
3. Visit a supported Canvas/Instructure page.
4. The extension reads assignment/submission data from the active Canvas session.
5. Newly synced submissions are sent to Canbet and awarded Bits.

Example sync response:

```json
{
  "created": 3,
  "bits_awarded": 600,
  "new_balance": 1600
}
```

### API Examples

Get the current user's account summary:

```http
GET /api/me/
```

Open a crate:

```http
POST /api/crate/open/
Content-Type: application/json

{
  "crate_type": "SPACE"
}
```

Example crate response:

```json
{
  "item": {
    "name": "Jupiter",
    "rarity": "RARE",
    "sprite_path": "sprites/Items/SpaceCollection/Jupiter.png"
  },
  "new_balance": 900,
  "crates_opened": 1
}
```

## Known Issues

- Demo video links still need to be added.
- Chrome extension approval is still pending.
- Local setup expects database configuration; the default settings are aimed at PostgreSQL-backed development and deployment.
- Canvas sync depends on a user's active Canvas session and supported Instructure page structure.
- Some project comments and older text appear to have encoding artifacts from previous edits.
- Individual contributor roles need to be confirmed by the team.

## Future Work

- Add final demo video links and screenshots.
- Finish Chrome Web Store approval and document install steps once available.
- Add seed data or a management command for quickly populating local lootboxes and item pools.
- Expand automated tests for crate odds, shop purchases, trade-ups, quicksell, and Canvas sync.
- Improve onboarding for first-time users and extension setup.
- Add richer item collection pages, achievements, and seasonal events.
- Add clearer admin documentation for managing items, lootboxes, and drop weights.
- Review encoding issues in older source comments and README history.

## Contributors

| Contributor | Role |
| --- | --- |
| Evan Williamson | Contributor; role to confirm |
| Jimmy Muhly Jr / Jimmy-cs01 | Contributor; role to confirm |
| Zane Lyvers / zlyvers | Contributor; role to confirm |
| Ethan / hartsfi | Contributor; role to confirm |
| Christian T. / PLOB | Contributor; role to confirm |

Contributor names are based on repository commit history. Replace the role placeholders with each team member's final project responsibilities, such as frontend, backend, extension, design/assets, testing, deployment, or documentation.

## Tech Stack

- Python
- Django
- Django REST Framework
- HTML
- CSS
- JavaScript
- Browser extension APIs
- PostgreSQL
- Docker
