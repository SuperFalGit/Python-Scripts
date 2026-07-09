# Notion Backup Script — Setup Guide

## Step 1: Install dependencies

Open a terminal on your Ubuntu laptop and run:

```bash
pip3 install notion-client python-dotenv --break-system-packages
```

## Step 2: Get your Notion API key

1. Go to **https://www.notion.so/my-integrations**
2. Click **"New integration"**
3. Name it something like `Ubuntu Backup`
4. Set workspace to your Notion workspace
5. Click **Submit**
6. Copy the **"Internal Integration Token"** (starts with `secret_...`)

## Step 3: Connect your Notion pages to the integration

For **each page** you want backed up:
1. Open the page in Notion
2. Click the **"..."** menu (top right)
3. Go to **Connections**
4. Find and add your `Ubuntu Backup` integration

> ⚠️ This step is easy to miss! Pages won't back up without it.

## Step 4: Create your .env file

In the same folder as `notion_backup.py`, create a file called `.env`:

```bash
nano .env
```

Add this line (replacing with your actual key):

```
NOTION_API_KEY=secret_xxxxxxxxxxxxxxxxxxxx
```

Save with `Ctrl+X`, then `Y`, then `Enter`.

## Step 5: Run the backup

```bash
python3 notion_backup.py
```

Your backed up pages will appear in:
```
~/notion_backup/YYYY-MM-DD/
```

## Step 6 (Optional): Schedule it to run weekly

To run every Sunday at 9am automatically:

```bash
crontab -e
```

Add this line:
```
0 9 * * 0 python3 /path/to/notion_backup.py
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Run the pip3 install command in Step 1 |
| `0 pages found` | Make sure you connected pages to the integration (Step 3) |
| `401 Unauthorized` | Check your API key in the .env file |
| Permission errors | Make sure the backup folder is writable |
