# sectxt-checker

**DISCLAIMER:** This project is generated with CoPilot, but manually tweaked and tested. No license is attached as I'm not sure where CoPilot based its code on.

---

Checks domain(s) for a valid security.txt

This tool reads a list of domains from a YAML configuration file and uses the [sectxt](https://github.com/DigitalTrustCenter/sectxt) library to validate their security.txt files.

## Installation

```bash
# 1. Create a virtual environment using uv
uv venv

# 2. Activate the virtual environment
source .venv/bin/activate

# 3. Install Python dependencies
uv pip install -r requirements.txt
```

## Configuration

Edit `config.yaml` to add the domains you want to check:

```yaml
domains:
  - github.com
  - example.com
  - google.com

# Minimum number of days the Expires field must be in the future (default: 30)
min_expiry_days: 30

# Enable healthcheck ping after script completion (default: false)
# Requires HEALTHCHECK_URL environment variable to be set
healthcheck_enabled: false
```

Configuration options:

- `domains`: List of domains to check (required)
- `min_expiry_days`: Minimum number of days the Expires field must be in the future (optional, default: 30)
- `healthcheck_enabled`: Enable sending a healthcheck ping after the script completes (optional, default: false)

## Usage

Make sure the virtual environment is activated, then run the checker:

```bash
source .venv/bin/activate  # if not already activated
python checker.py
```

### Healthcheck

To enable healthcheck pings (useful for monitoring tools like Healthchecks.io):

1. Set the `healthcheck_enabled` option to `true` in `config.yaml`
2. Set the `HEALTHCHECK_URL` environment variable:

```bash
export HEALTHCHECK_URL="https://hc-ping.com/your-uuid-here"
python checker.py
```

The healthcheck ping will be sent after all domains are checked, regardless of whether the checks succeeded or failed.

## How it works

1. Load domains from `config.yaml`
2. Check each domain's `security.txt` file
3. Display a progress indicator for each domain
4. Print detailed results including errors, recommendations, and notifications
5. Provide a summary of all checks

## Output

The tool provides three levels of feedback:

- **Errors**: Issues that make the security.txt file invalid
- **Recommendations**: Best practices that should be followed
- **Notifications**: Informational messages about the file
