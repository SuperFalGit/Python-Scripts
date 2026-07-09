#!/usr/bin/env python3
"""
========================================================
  NOTION TO MARKDOWN BACKUP SCRIPT
  Author: Built with Claude for Iain Wall (SuperFalGit)
  Purpose: Backs up all Notion pages to local Markdown
           files on your Ubuntu desktop
    Note that this needs config for file names etc!
========================================================

WHAT THIS SCRIPT DOES:
  1. Connects to your Notion workspace via the Notion API
  2. Finds all pages you have access to
  3. Converts each page's content to Markdown format
  4. Saves them as .md files in a local backup folder
  5. Organises them by date so you have a history

HOW TO RUN IT:
  1. Install dependencies (one time only):
       pip3 install notion-client python-dotenv --break-system-packages

  2. Create a .env file in the same folder as this script:
       NOTION_API_KEY=your_secret_key_here

  3. Run the script:
       python3 notion_backup.py

WHERE TO GET YOUR NOTION API KEY:
  1. Go to https://www.notion.so/my-integrations
  2. Click "New integration"
  3. Give it a name like "Ubuntu Backup"
  4. Copy the "Internal Integration Token"
  5. IMPORTANT: In Notion, open each page you want backed up,
     click the "..." menu, go to "Connections" and add your integration

"""

# ============================================================
# IMPORTS — bringing in the tools we need
# ============================================================
# Python comes with lots of built-in tools, and we can also
# install extra ones (like notion-client). Here we import
# everything we'll need throughout the script.

import os           # os = operating system tools (create folders, check paths etc)
import json         # json = handle JSON data (what APIs send back to us)
import re           # re = regular expressions (for cleaning up text)
from datetime import datetime   # for getting today's date and time
from pathlib import Path        # a modern way to handle file/folder paths
from dotenv import load_dotenv  # reads our .env file safely
from notion_client import Client  # the Notion API wrapper

# ============================================================
# CONFIGURATION — settings for the script
# ============================================================
# load_dotenv() reads the .env file and makes the variables
# inside it available via os.environ.get()
# This keeps sensitive info like API keys out of the script itself
# — good security practice!

load_dotenv()

# os.environ.get() fetches the value from our .env file
# If the key doesn't exist, it returns None
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")

# pathlib's Path() creates a path object
# Path.home() = your home directory (e.g. /home/iain)
# The / operator joins path segments together (neat Python trick!)
BACKUP_BASE_DIR = Path.home() / "notion_backup"

# datetime.now() gets the current date and time
# .strftime() formats it as a string — here: YYYY-MM-DD
# This means each day's backup goes in its own folder
TODAY = datetime.now().strftime("%Y-%m-%d")

# The final backup folder will be something like:
# /home/iain/notion_backup/2025-01-15/
BACKUP_DIR = BACKUP_BASE_DIR / TODAY


# ============================================================
# HELPER FUNCTIONS
# ============================================================
# Functions are reusable blocks of code. We define them once
# here and call them later in the main script.
# def = "define a function"

def create_backup_directory():
    """
    Creates the backup folder if it doesn't already exist.
    The exist_ok=True means it won't error if the folder is there.
    """
    # parents=True creates any missing parent folders too
    # exist_ok=True means no error if folder already exists
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"📁 Backup folder ready: {BACKUP_DIR}")


def clean_filename(title):
    """
    Turns a Notion page title into a safe filename.
    e.g. "S1 Purple AI: Training Notes!" becomes "S1_Purple_AI_Training_Notes"

    re.sub() = substitute — replaces characters matching a pattern
    [^\\w\\s-] = any character that ISN'T a word character, space, or hyphen
    .strip() = removes leading/trailing whitespace
    .replace() = swaps spaces for underscores
    """
    # Remove any character that isn't a letter, number, space, or hyphen
    clean = re.sub(r'[^\w\s-]', '', title)
    # Strip extra whitespace from start and end
    clean = clean.strip()
    # Replace spaces with underscores (filenames work better without spaces)
    clean = clean.replace(' ', '_')
    return clean


def get_page_title(page):
    """
    Extracts the title from a Notion page object.
    Notion stores titles in a nested structure, so we
    need to dig through it carefully.

    The 'or' keyword provides a fallback value if something is None/empty.
    """
    try:
        # Notion page titles are stored in properties > title > title array
        # Each element has a 'plain_text' field with the actual text
        title_array = page.get("properties", {}).get("title", {}).get("title", [])

        # If there's content in the array, join it all into one string
        if title_array:
            # This is a "list comprehension" — a compact way to loop
            # It means: for each item in title_array, get its plain_text value
            return " ".join([item.get("plain_text", "") for item in title_array])

        # Some pages store the title differently (as 'Name' property)
        name_array = page.get("properties", {}).get("Name", {}).get("title", [])
        if name_array:
            return " ".join([item.get("plain_text", "") for item in name_array])

        # If we can't find a title, use the page ID as a fallback
        return page.get("id", "Untitled")

    except Exception:
        # If anything goes wrong, return a safe fallback
        # This stops the whole script crashing on one bad page
        return "Untitled"


def block_to_markdown(block):
    """
    Converts a single Notion block into Markdown text.

    Notion stores page content as "blocks" — each paragraph,
    heading, bullet point etc is its own block with a type.
    We check the type and convert it to the Markdown equivalent.

    Markdown reference:
      # Heading 1    = h1
      ## Heading 2   = h2
      **bold**       = bold text
      `code`         = inline code
      > quote        = blockquote
      - item         = bullet point
      1. item        = numbered list
    """

    # Get the block type (e.g. "paragraph", "heading_1", "bulleted_list_item")
    block_type = block.get("type", "")

    # Get the content for this block type
    # block[block_type] gives us the data for whatever type this block is
    block_data = block.get(block_type, {})

    # Extract the rich text array (where the actual text lives)
    rich_text = block_data.get("rich_text", [])

    # Helper: extract plain text from rich_text array
    # This is an "inline function" (lambda) — a quick one-liner function
    get_text = lambda rt: "".join([t.get("plain_text", "") for t in rt])

    text = get_text(rich_text)

    # ---- Convert each block type to its Markdown equivalent ----

    if block_type == "heading_1":
        return f"# {text}\n\n"          # # Big heading

    elif block_type == "heading_2":
        return f"## {text}\n\n"         # ## Medium heading

    elif block_type == "heading_3":
        return f"### {text}\n\n"        # ### Small heading

    elif block_type == "paragraph":
        return f"{text}\n\n" if text else "\n"  # Normal paragraph

    elif block_type == "bulleted_list_item":
        return f"- {text}\n"            # - Bullet point

    elif block_type == "numbered_list_item":
        return f"1. {text}\n"           # 1. Numbered item

    elif block_type == "to_do":
        # Checkboxes — checked or unchecked
        checked = block_data.get("checked", False)
        checkbox = "x" if checked else " "
        return f"- [{checkbox}] {text}\n"  # - [x] Done  or  - [ ] Todo

    elif block_type == "toggle":
        return f"<details><summary>{text}</summary>\n\n</details>\n\n"

    elif block_type == "quote":
        return f"> {text}\n\n"          # > Blockquote

    elif block_type == "callout":
        # Callout boxes — Notion uses these for highlighted info
        emoji = block_data.get("icon", {}).get("emoji", "💡")
        return f"> {emoji} **{text}**\n\n"

    elif block_type == "code":
        # Code blocks — preserve the language if specified
        language = block_data.get("language", "")
        code_text = get_text(block_data.get("rich_text", []))
        return f"```{language}\n{code_text}\n```\n\n"

    elif block_type == "divider":
        return "---\n\n"                # Horizontal line

    elif block_type == "table_of_contents":
        return ""                       # Skip — markdown doesn't need this

    elif block_type == "image":
        # Try to get the image URL
        image_data = block_data
        url = ""
        if image_data.get("type") == "external":
            url = image_data.get("external", {}).get("url", "")
        elif image_data.get("type") == "file":
            url = image_data.get("file", {}).get("url", "")
        caption = get_text(image_data.get("caption", []))
        return f"![{caption}]({url})\n\n" if url else ""

    elif block_type == "bookmark":
        url = block_data.get("url", "")
        caption = get_text(block_data.get("caption", []))
        label = caption if caption else url
        return f"[{label}]({url})\n\n"

    else:
        # For any block type we haven't handled, just get the text
        # This is a safe fallback so we don't lose content
        if text:
            return f"{text}\n\n"
        return ""


def page_to_markdown(notion, page):
    """
    Converts a full Notion page to a Markdown string.

    This function:
    1. Gets the page title
    2. Fetches all the blocks (content) from the page
    3. Converts each block to Markdown
    4. Joins it all together with a header

    'notion' here is our API client — we pass it in so we can
    make more API calls to get the page content.
    """

    title = get_page_title(page)
    page_id = page.get("id", "")

    print(f"  📄 Converting: {title}")

    # Start building our markdown string
    # We add a header with the title and backup date
    markdown_lines = [
        f"# {title}\n",
        f"\n> *Backed up from Notion on {TODAY}*\n",
        f"> *Page ID: {page_id}*\n",
        "\n---\n\n"
    ]

    try:
        # Fetch the page content (blocks) from the Notion API
        # notion.blocks.children.list() returns all blocks on a page
        blocks_response = notion.blocks.children.list(block_id=page_id)

        # The actual blocks are in the "results" key of the response
        blocks = blocks_response.get("results", [])

        # Notion paginates results — if has_more is True, there are more blocks
        # We keep fetching until we have them all
        while blocks_response.get("has_more"):
            # next_cursor tells the API where we left off
            next_cursor = blocks_response.get("next_cursor")
            blocks_response = notion.blocks.children.list(
                block_id=page_id,
                start_cursor=next_cursor
            )
            # += adds the new blocks to our existing list
            blocks += blocks_response.get("results", [])

        # Convert each block to markdown and add to our lines
        # This is a for loop — it processes each block one at a time
        for block in blocks:
            markdown_lines.append(block_to_markdown(block))

    except Exception as e:
        # If we can't get the content (e.g. permissions issue), note it
        markdown_lines.append(f"\n⚠️ *Could not retrieve page content: {e}*\n")

    # "".join() concatenates (joins) all strings in the list into one big string
    return "".join(markdown_lines)


def save_markdown(title, content):
    """
    Saves a markdown string to a .md file in the backup directory.

    'f strings' (f"...") let us embed variables directly in strings
    using curly braces {like_this}
    """

    # Create a safe filename from the page title
    filename = clean_filename(title) + ".md"

    # Build the full file path
    filepath = BACKUP_DIR / filename

    # Open the file for writing ('w' = write mode)
    # encoding='utf-8' ensures special characters save correctly
    # 'with' ensures the file is properly closed after writing
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"    ✅ Saved: {filename}")
    return filepath


def run_backup():
    """
    MAIN FUNCTION — this is where everything comes together.
    It orchestrates all the steps of the backup process.
    """

    # ---- Step 1: Check we have an API key ----
    if not NOTION_API_KEY:
        print("❌ ERROR: No Notion API key found!")
        print("   Create a .env file with: NOTION_API_KEY=your_key_here")
        print("   Get your key from: https://www.notion.so/my-integrations")
        return  # 'return' exits the function early

    # ---- Step 2: Create the backup folder ----
    print("\n🚀 Starting Notion backup...\n")
    create_backup_directory()

    # ---- Step 3: Connect to the Notion API ----
    # Client() creates our connection to Notion using our API key
    notion = Client(auth=NOTION_API_KEY)
    print("✅ Connected to Notion API\n")

    # ---- Step 4: Get all pages we have access to ----
    print("🔍 Searching for pages...\n")

    try:
        # notion.search() finds everything our integration can access
        # filter={"property": "object", "value": "page"} = pages only (not databases)
        search_response = notion.search(
            filter={"property": "object", "value": "page"}
        )

        pages = search_response.get("results", [])

        # Handle pagination — same as with blocks above
        while search_response.get("has_more"):
            next_cursor = search_response.get("next_cursor")
            search_response = notion.search(
                filter={"property": "object", "value": "page"},
                start_cursor=next_cursor
            )
            pages += search_response.get("results", [])

        print(f"📚 Found {len(pages)} pages to back up\n")

    except Exception as e:
        print(f"❌ ERROR connecting to Notion: {e}")
        print("   Check your API key and make sure your integration has access")
        return

    # ---- Step 5: Convert and save each page ----
    print("💾 Converting and saving pages...\n")

    # Keep track of how many succeed and fail
    success_count = 0
    fail_count = 0

    # Loop through every page we found
    for page in pages:
        try:
            title = get_page_title(page)

            # Convert the page to markdown
            markdown_content = page_to_markdown(notion, page)

            # Save it to a file
            save_markdown(title, markdown_content)

            success_count += 1

        except Exception as e:
            # If one page fails, log it and continue with the rest
            # We don't want one bad page to stop the whole backup
            print(f"    ⚠️  Failed to backup '{title}': {e}")
            fail_count += 1

    # ---- Step 6: Print summary ----
    print(f"\n{'='*50}")
    print(f"✅ Backup complete!")
    print(f"   Pages saved:  {success_count}")
    print(f"   Pages failed: {fail_count}")
    print(f"   Location:     {BACKUP_DIR}")
    print(f"{'='*50}\n")

    # ---- Step 7: Create an index file ----
    # A handy index.md listing all backed up pages
    create_index(pages)


def create_index(pages):
    """
    Creates an index.md file listing all backed up pages.
    This gives you a quick overview of everything in the backup.
    """

    index_lines = [
        "# Notion Backup Index\n\n",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n",
        "---\n\n",
        "## Pages Backed Up\n\n"
    ]

    # Loop through pages and add each one to the index
    for page in pages:
        title = get_page_title(page)
        filename = clean_filename(title) + ".md"
        # Create a relative link to each file
        index_lines.append(f"- [{title}](./{filename})\n")

    # Write the index file
    index_path = BACKUP_DIR / "index.md"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.writelines(index_lines)

    print(f"📋 Index created: {index_path}\n")


# ============================================================
# ENTRY POINT
# ============================================================
# This is standard Python — it means "only run this code if
# this script is being run directly" (not imported by another script)
# Think of it as the "on" switch for the whole script.

if __name__ == "__main__":
    run_backup()
