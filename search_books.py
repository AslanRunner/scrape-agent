"""
Web Scraping with BeautifulSoup: Day 3 - Search & Analyze the Scraped Data.
Interactive command-line search engine and REPL for querying, filtering,
sorting, and analyzing scraped catalog data with pandas.
"""
import os
import sys
import pandas as pd

# Force UTF-8 output on Windows terminal
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

CSV_DEFAULT_FILE = "all_books.csv"


def load_dataset(csv_path: str = CSV_DEFAULT_FILE) -> pd.DataFrame:
    """Load the scraped books CSV into a typed pandas DataFrame."""
    if not os.path.exists(csv_path):
        # Fallback to books.csv if all_books.csv hasn't been scraped yet
        if os.path.exists("books.csv"):
            print(f"[i] '{csv_path}' not found. Loading 'books.csv' instead.")
            csv_path = "books.csv"
        else:
            print(f"[!] Error: Dataset '{csv_path}' not found.")
            print("[i] Run 'python scrape_all_books.py' or 'python scrape_books.py' first to generate the dataset.")
            sys.exit(1)

    df = pd.read_csv(csv_path, encoding="utf-8")

    # Clean & ensure numeric types
    if "price" in df.columns:
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0.0)
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0).astype(int)
    if "stock_count" in df.columns:
        df["stock_count"] = pd.to_numeric(df["stock_count"], errors="coerce").fillna(0).astype(int)
    else:
        df["stock_count"] = 1

    if "category" not in df.columns:
        df["category"] = "General"

    if "description" not in df.columns:
        df["description"] = ""

    return df


def show_results(df: pd.DataFrame, header_message: str = ""):
    """Format and display aligned tabular search results."""
    if header_message:
        print(f"\n{header_message}")
    if df.empty:
        print("  (no results)")
        return

    print()
    print(f"  {'Title':<40} {'Category':<18} {'Price':>8} {'Rating':>10}")
    print("  " + "-" * 78)

    for _, row in df.head(20).iterrows():
        title = str(row["title"])
        if len(title) > 40:
            title = title[:37] + "..."
        stars = "*" * int(row["rating"])
        cat = str(row["category"])
        if len(cat) > 18:
            cat = cat[:15] + "..."
        price_str = f"£{row['price']:.2f}"
        print(f"  {title:<40} {cat:<18} {price_str:>8} {stars:>10}")

    if len(df) > 20:
        print(f"\n  (showing top 20 of {len(df)} matches)")


def command_search(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """Case-insensitive keyword search across title, description, and category."""
    if not query:
        print("  Usage: search <keyword>")
        return df

    title_match = df["title"].astype(str).str.contains(query, case=False, na=False)
    desc_match = df["description"].astype(str).str.contains(query, case=False, na=False)
    cat_match = df["category"].astype(str).str.contains(query, case=False, na=False)

    matches = df[title_match | desc_match | cat_match]
    show_results(matches, f"Found {len(matches)} matches for '{query}':")
    return matches


def command_filter(full_df: pd.DataFrame, args: list[str]) -> pd.DataFrame:
    """Apply boolean masks across category, price, and rating."""
    if not args:
        print("  Usage: filter category=<name> min_price=<num> max_price=<num> rating>=<1-5>")
        return full_df

    mask = pd.Series(True, index=full_df.index)
    applied = []

    for arg in args:
        if arg.startswith("category="):
            value = arg.split("=", 1)[1].lower()
            mask &= full_df["category"].astype(str).str.lower().str.contains(value, na=False)
            applied.append(f"category={value}")
        elif arg.startswith("min_price="):
            try:
                val = float(arg.split("=", 1)[1])
                mask &= full_df["price"] >= val
                applied.append(f"price>={val}")
            except ValueError:
                print(f"  Could not parse min_price: {arg}")
        elif arg.startswith("max_price="):
            try:
                val = float(arg.split("=", 1)[1])
                mask &= full_df["price"] <= val
                applied.append(f"price<={val}")
            except ValueError:
                print(f"  Could not parse max_price: {arg}")
        elif "rating>=" in arg:
            try:
                val = int(arg.split(">=", 1)[1])
                mask &= full_df["rating"] >= val
                applied.append(f"rating>={val}")
            except ValueError:
                print(f"  Could not parse rating: {arg}")
        elif arg.startswith("rating="):
            try:
                val = int(arg.split("=", 1)[1])
                mask &= full_df["rating"] == val
                applied.append(f"rating={val}")
            except ValueError:
                print(f"  Could not parse rating: {arg}")
        elif arg.startswith("min_stock="):
            try:
                val = int(arg.split("=", 1)[1])
                mask &= full_df["stock_count"] >= val
                applied.append(f"stock>={val}")
            except ValueError:
                print(f"  Could not parse min_stock: {arg}")
        else:
            print(f"  Unknown filter argument: '{arg}'. Ignored.")

    result = full_df[mask]
    if applied:
        print(f"\nFilter applied: {', '.join(applied)}")
        show_results(result, f"{len(result)} books match.")
    return result


def command_sort(current_df: pd.DataFrame, args: list[str]) -> pd.DataFrame:
    """Sort the current view by any column without permanently modifying the filtered state."""
    if not args:
        print("  Usage: sort <field> [asc|desc]")
        return current_df

    field = args[0].lower()
    ascending = not (len(args) > 1 and args[1].lower() == "desc")

    if field not in current_df.columns:
        print(f"  Unknown field: '{field}'. Available: {', '.join(current_df.columns)}")
        return current_df

    direction = "ascending" if ascending else "descending"
    sorted_df = current_df.sort_values(field, ascending=ascending)
    show_results(sorted_df.head(10), f"Sorted by {field} ({direction}). Showing top 10:")
    return current_df


def command_stats(df: pd.DataFrame) -> None:
    """Display comprehensive summary statistics and distributions."""
    if df.empty:
        print("\n  No books in current view.")
        return

    total = len(df)
    categories_cnt = df["category"].nunique()
    avg_price = df["price"].mean()
    min_price = df["price"].min()
    max_price = df["price"].max()
    avg_rating = df["rating"].mean()
    in_stock = (df["stock_count"] > 0).sum()
    pct_stock = (in_stock / total) * 100 if total > 0 else 0

    print(f"\n  Books:            {total}")
    print(f"  Categories:       {categories_cnt}")
    print(f"  Average price:    £{avg_price:.2f}")
    print(f"  Price range:      £{min_price:.2f} - £{max_price:.2f}")
    print(f"  Avg rating:       {avg_rating:.2f} / 5")
    print(f"  In stock:         {in_stock} ({pct_stock:.0f}%)")

    print("\n  Rating breakdown:")
    for rating in range(1, 6):
        count = (df["rating"] == rating).sum()
        stars = "*" * rating
        print(f"    {stars:<13} {count:>3}")

    print("\n  Top 5 categories by book count:")
    top = df["category"].value_counts().head(5)
    for cat, count in top.items():
        print(f"    {cat:<22} {count:>3}")


def command_save(current_df: pd.DataFrame, args: list[str]) -> pd.DataFrame:
    """Export current view to a CSV file."""
    if not args:
        print("  Usage: save <filename.csv>")
        return current_df

    filename = args[0]
    try:
        current_df.to_csv(filename, index=False, encoding="utf-8")
        print(f"\n✓ Exported {len(current_df)} books to {filename}")
    except Exception as e:
        print(f"  Error saving to {filename}: {e}")
    return current_df


def print_help() -> None:
    """Print available commands and syntax."""
    print("""
Available Commands:
  stats                                   Show catalog / view statistics & distribution
  search <keyword>                        Search title, category, and description
  filter <criteria...>                    Filter catalog from full dataset
                                          Examples:
                                            filter category=Mystery
                                            filter min_price=20 max_price=40
                                            filter category=Fiction rating>=4
  sort <field> [asc|desc]                 Sort current view by field (price, rating, title, etc.)
  save <filename.csv>                     Export the active view to a CSV file
  reset                                   Clear all filters and return to full catalog
  help                                    Show this command guide
  quit / exit                             Exit the REPL session
""")


def handle_command(line: str, df: pd.DataFrame, current: pd.DataFrame) -> pd.DataFrame:
    """Dispatch user input to appropriate command handler."""
    parts = line.split()
    cmd = parts[0].lower()
    args = parts[1:]

    if cmd == "stats":
        command_stats(current)
        return current
    elif cmd == "search":
        return command_search(current, " ".join(args))
    elif cmd == "filter":
        return command_filter(df, args)
    elif cmd == "sort":
        return command_sort(current, args)
    elif cmd == "save":
        return command_save(current, args)
    elif cmd == "reset":
        print(f"\nFilters cleared. {len(df)} books in view.")
        return df
    elif cmd in ("help", "?"):
        print_help()
        return current
    else:
        print(f"  Unknown command: '{cmd}'. Type 'help' for the list.")
        return current


def run_repl(df: pd.DataFrame) -> None:
    """Run interactive Read-Eval-Print Loop."""
    print("=" * 70)
    print(f"BOOK CATALOG SEARCH - {len(df)} books loaded from {CSV_DEFAULT_FILE}")
    print("=" * 70)
    print("\nType 'help' for commands, 'quit' to exit.\n")

    current = df

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue
            if line.lower() in ("quit", "exit", "q"):
                print("\nGoodbye!")
                break

            current = handle_command(line, df, current)
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


def main():
    csv_file = sys.argv[1] if len(sys.argv) > 1 else CSV_DEFAULT_FILE
    df = load_dataset(csv_file)
    run_repl(df)


if __name__ == "__main__":
    main()
