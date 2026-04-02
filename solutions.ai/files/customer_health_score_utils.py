import io, csv


def parse_lightdash_csv_data(csv_string):
    ################ FORMAT LDASH DATA ################

    """
    Parses CSV data from Lightdash, expecting two columns:
    1. FCT Instances (Daily) Weeks Since Update
    2. FCT Instance Flow Executions (Daily) Total Flow Runs (may contain commas)
    """
    # Use io.StringIO to treat the string as a file
    csvfile = io.StringIO(csv_string.strip())

    # Use the csv reader. Assuming comma delimiter and quoting for numbers like "1,167"
    reader = csv.reader(csvfile, delimiter=",", quotechar='"')

    # Skip header row
    try:
        next(reader)
    except StopIteration:
        # Handle empty file case
        return 0, 0, 0

    current_period_runs = 0
    previous_period_runs = 0
    total_runs = 0

    # We expect Row 0 (current) and Row 1 (previous)
    for i, row in enumerate(reader):
        if len(row) < 2:
            continue

        try:
            # The runs column may contain a comma separator (e.g., "1,167"), remove it before conversion
            runs_str = row[1].replace('"', "").replace(",", "")
            runs = int(runs_str)
        except ValueError:
            print(f"Warning: Could not parse run count from row: {row}")
            runs = 0

        # Row 0 is current week, Row 1 is previous week
        if i == 0:
            current_period_runs = runs
        elif i == 1:
            previous_period_runs = runs

        total_runs += runs

    return current_period_runs, previous_period_runs


def analyze_pylon_issues(issues):
    # --- Helper Functions for Pylon Issue Analysis ---
    """Analyzes issue data to count priority levels and determine general sentiment."""
    p1_p2_count = 0
    p0_count = 0
    sentiment_counts = {"positive": 0, "neutral": 0, "negative": 0}

    # Define states considered 'open' for counting
    open_states = ["new", "waiting_on_you", "waiting_on_customer", "on_hold"]
    # Define P1/P2 priorities (assuming 'critical' and 'high' are the highest)
    high_priorities = ["high", "normal"]
    p0_category = "critical"

    for issue in issues:
        # Check if the issue is still active/open
        if issue.get("state") in open_states:
            # Count P1/P2 issues
            priority = (
                issue.get("custom_fields", {})
                .get("priority", {})
                .get("value", "low")
                .lower()
            )
            if priority in high_priorities:
                p1_p2_count += 1
            elif priority == p0_category:
                p0_category += 1

            # Tally Sentiment
            sentiment = (
                issue.get("custom_fields", {})
                .get("sentiment_analysis", {})
                .get("value", "neutral")
                .lower()
            )
            if sentiment in sentiment_counts:
                sentiment_counts[sentiment] += 1

    # Calculate overall sentiment based on open issues
    if sentiment_counts["negative"] > sentiment_counts["positive"]:
        overall_sentiment = "negative"
    elif sentiment_counts["positive"] > 0:
        overall_sentiment = "positive"
    else:
        overall_sentiment = "neutral"

    return p1_p2_count, overall_sentiment, p0_count


def analyze_license_risk(license_data):
    import pendulum

    """
    Calculates license risk based on the earliest active, future-dated license.
    If no active licenses are in the future, critical risk is assigned.
    """
    TODAY = pendulum.now()
    active_future_dates = []

    # 1. Filter for active licenses with future expiration dates
    for license in license_data:
        try:
            exp_date = pendulum.parse(license.get("expirationDate"))
            # is_active = license.get('isActive', False) # Default to False if field is missing

            if exp_date > TODAY:
                active_future_dates.append(exp_date)

        except Exception:
            # Skip malformed license entries
            continue

    # 2. Determine Days to Expiry and Risk
    if active_future_dates:
        # Get the EARLIEST future-active expiration date (highest risk point)
        earliest_expiry = min(active_future_dates)
        days_to_expiry = (earliest_expiry - TODAY).in_days()
    else:
        # CRITICAL RISK: No active, non-expired licenses found.
        # Set days_to_expiry to a large negative number (e.g., -365 days) for max penalty
        days_to_expiry = 0

    return days_to_expiry
