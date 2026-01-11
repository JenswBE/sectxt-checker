#!/usr/bin/env python3
"""
Security.txt Checker
Reads domains from a YAML config file and checks their security.txt files.
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
import yaml
from sectxt import SecurityTXT


@dataclass
class Config:
    """Configuration for the security.txt checker."""
    domains: list[str]
    min_expiry_days: int = field(default=30)
    healthcheck_enabled: bool = field(default=False)

    def __post_init__(self):
        """Validate configuration after initialization."""
        if not isinstance(self.domains, list):
            raise ValueError("'domains' must be a list")
        if not self.domains:
            raise ValueError("'domains' list cannot be empty")
        for idx, domain in enumerate(self.domains):
            if not isinstance(domain, str) or not domain.strip():
                raise ValueError(f"Invalid domain at index {idx}: {domain}")
        if not isinstance(self.min_expiry_days, int) or self.min_expiry_days < 0:
            raise ValueError("'min_expiry_days' must be a non-negative integer")
        if not isinstance(self.healthcheck_enabled, bool):
            raise ValueError("'healthcheck_enabled' must be a boolean")


def load_config(config_file: str | Path) -> Config:
    """Load configuration from the YAML config file."""
    config_path = Path(config_file)

    try:
        with config_path.open('r') as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise ValueError("Config file must contain a YAML dictionary")

        return Config(**data)

    except FileNotFoundError:
        print(f"Error: Config file '{config_file}' not found.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error: Invalid YAML in config file: {e}")
        sys.exit(1)
    except (ValueError, TypeError) as e:
        print(f"Error: Invalid configuration: {e}")
        sys.exit(1)


def check_domain(domain: str, min_expiry_days: int = 30) -> dict:
    """Check a single domain's security.txt file."""
    print(f"Checking {domain}...", end=' ', flush=True)

    try:
        s = SecurityTXT(domain)

        # Start with the standard validation results
        errors = list(s.errors)

        # Add custom validation for minimum expiry date
        if hasattr(s, '_expires_date') and s._expires_date:
            min_expiry_date = datetime.now(timezone.utc) + timedelta(days=min_expiry_days)
            if s._expires_date < min_expiry_date:
                days_until_expiry = (s._expires_date - datetime.now(timezone.utc)).days
                errors.append({
                    'code': 'expiry_too_soon',
                    'message': f"Expires date is only {days_until_expiry} day(s) in the future, but must be at least {min_expiry_days} day(s).",
                    'line': None
                })

        result = {
            'domain': domain,
            'is_valid': len(errors) == 0,
            'errors': errors,
            'recommendations': s.recommendations,
            'notifications': s.notifications
        }

        if result['is_valid']:
            print("✓ Valid")
        else:
            print(f"✗ Invalid ({len(errors)} error(s))")

        return result

    except Exception as e:
        print(f"✗ Failed: {e}")
        return {
            'domain': domain,
            'is_valid': False,
            'error': str(e),
            'errors': [],
            'recommendations': [],
            'notifications': []
        }


def print_results(results: list[dict]):
    """Print detailed results for all domains."""
    print("\n" + "=" * 80)
    print("DETAILED RESULTS")
    print("=" * 80 + "\n")

    for result in results:
        domain = result['domain']
        print(f"\n{'=' * 80}")
        print(f"Domain: {domain}")
        print(f"Valid: {'Yes ✓' if result['is_valid'] else 'No ✗'}")
        print(f"{'=' * 80}")

        # Print general error (if any)
        if 'error' in result:
            print(f"\nGeneral Error: {result['error']}")
            continue

        # Print errors
        if result['errors']:
            print(f"\nErrors ({len(result['errors'])}):")
            for error in result['errors']:
                line_info = f" (line {error['line']})" if error['line'] else ""
                print(f"  - [{error['code']}]{line_info}: {error['message']}")
        else:
            print("\nNo errors found.")

        # Print recommendations
        if result['recommendations']:
            print(f"\nRecommendations ({len(result['recommendations'])}):")
            for rec in result['recommendations']:
                line_info = f" (line {rec['line']})" if rec['line'] else ""
                print(f"  - [{rec['code']}]{line_info}: {rec['message']}")

        # Print notifications
        if result['notifications']:
            print(f"\nNotifications ({len(result['notifications'])}):")
            for note in result['notifications']:
                line_info = f" (line {note['line']})" if note['line'] else ""
                print(f"  - [{note['code']}]{line_info}: {note['message']}")


def print_summary(results: list[dict]):
    """Print a summary of all checks."""
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    total = len(results)
    valid = sum(1 for r in results if r['is_valid'])
    invalid = total - valid

    print(f"\nTotal domains checked: {total}")
    print(f"Valid: {valid}")
    print(f"Invalid: {invalid}")

    if invalid > 0:
        print("\nDomains with issues:")
        for result in results:
            if not result['is_valid']:
                error_count = len(result.get('errors', []))
                print(f"  - {result['domain']} ({error_count} error(s))")


def send_healthcheck():
    """Send a GET request to the healthcheck URL from the environment variable."""
    healthcheck_url = os.getenv('HEALTHCHECK_URL')

    if not healthcheck_url:
        print("\nError: HEALTHCHECK_URL environment variable not set. Exiting.")
        sys.exit(1)

    try:
        print(f"\nSending healthcheck to value of env var HEALTHCHECK_URL ...", end=' ', flush=True)
        response = requests.get(healthcheck_url, timeout=10)
        if response.status_code == 200:
            print("✓ Success")
        else:
            print(f"✗ Failed with status code {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Failed: {e}")


def main():
    config_file = 'config.yaml'

    # Load configuration
    config = load_config(config_file)

    print(f"Loaded {len(config.domains)} domain(s) from {config_file}")
    print(f"Minimum expiry: {config.min_expiry_days} day(s) in the future\n")

    exit_code = 0

    try:
        # Check all domains
        results = []
        for domain in config.domains:
            result = check_domain(domain, min_expiry_days=config.min_expiry_days)
            results.append(result)

        # Print detailed results
        print_results(results)

        # Print summary
        print_summary(results)

        # Set exit code if any domains are invalid
        if any(not result['is_valid'] for result in results):
            exit_code = 1

    finally:
        # Send healthcheck if enabled
        if config.healthcheck_enabled:
            send_healthcheck()

        sys.exit(exit_code)


if __name__ == '__main__':
    main()
