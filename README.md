# Folk CRM MCP Server

An MCP (Model Context Protocol) server that provides access to [Folk CRM](https://folk.app) functionality, allowing AI assistants to manage contacts, companies, notes, reminders, and more.

## Features

- **Smart Search**: Find people and companies by name with minimal token usage
- **Two-Phase Lookup**: Quick search returns IDs, then fetch full details as needed
- **Contact Management**: Create, update, and delete people and companies
- **Notes & Reminders**: Attach context to your contacts
- **Interaction Logging**: Track emails, meetings, and calls

## Adding to Claude Code

### From Registry (Published)

```bash
# Configure your Folk API key
mpak config set @nimblebraininc/folk api_key=your_api_key_here

# Add to Claude Code
claude mcp add folk -- mpak run @nimblebraininc/folk
```

### Local Development

```bash
# Clone and enter the repo
git clone https://github.com/NimbleBrainInc/mcp-folk.git
cd mcp-folk

# Install dependencies
uv sync

# Build the bundle
make pack

# Configure your API key
mpak config set @nimblebraininc/folk api_key=your_api_key_here

# Add to Claude Code (use absolute path)
claude mcp add folk -- mpak run --local /path/to/mcp-folk/mcp-folk-0.1.0-darwin-arm64.mcpb
```

## Configuration

### Getting Your Folk API Key

1. Log in to your Folk workspace
2. Go to **Settings > API**
3. Create a new API key
4. Copy the key and configure with `mpak config set`

## Available Tools

### Search (Use First)

| Tool | Purpose |
|------|---------|
| `find_person(name)` | Find people by name, returns `{found, matches: [{id, name, email}]}` |
| `find_company(name)` | Find companies by name, returns `{found, matches: [{id, name, industry}]}` |

### Details (After Finding)

| Tool | Purpose |
|------|---------|
| `get_person_details(person_id)` | Full person info including all fields |
| `get_company_details(company_id)` | Full company info including all fields |

### Browse

| Tool | Purpose |
|------|---------|
| `browse_people(page, per_page)` | Paginated list of all people |
| `browse_companies(page, per_page)` | Paginated list of all companies |

### Groups & Filtering

| Tool | Purpose |
|------|---------|
| `list_groups()` | List all groups in the workspace |
| `find_people_in_group(group_name, status)` | Find people in a group, optionally filtered by Status |
| `find_companies_in_group(group_name, status)` | Find companies in a group, optionally filtered by Status |

### Actions

| Tool | Purpose |
|------|---------|
| `add_person(first_name, ...)` | Create new person |
| `add_company(name, ...)` | Create new company |
| `update_person(person_id, ...)` | Update person fields |
| `update_company(company_id, ...)` | Update company fields |
| `delete_person(person_id)` | Delete a person |
| `delete_company(company_id)` | Delete a company |

### Notes & Reminders

| Tool | Purpose |
|------|---------|
| `add_note(person_id, content)` | Add note to person |
| `get_notes(person_id)` | Get notes for person |
| `set_reminder(person_id, reminder, when)` | Set a reminder |
| `log_interaction(person_id, type, when)` | Log an interaction |

### Utility

| Tool | Purpose |
|------|---------|
| `whoami()` | Get current authenticated user |

## Common Use Cases

**Look up contacts**
- "Is Sarah Chen in my CRM?"
- "Find everyone at Acme Corp"
- "What's John's email?"

**Add contacts after meetings**
- "Add Mike Johnson from today's meeting, he's a PM at Stripe"
- "Create a contact for lisa@example.com"

**Take notes**
- "Add a note to Sarah: discussed Q2 roadmap, she's interested in enterprise plan"
- "What are my notes on the Acme deal?"

**Set follow-ups**
- "Remind me to follow up with John next Tuesday"
- "Set a reminder to check in with Sarah in 2 weeks"

**Log interactions**
- "Log that I had a call with Mike today"
- "Record my meeting with the Acme team"

**Browse contacts**
- "Show me my recent contacts"
- "List all companies in my CRM"

**Query groups and pipelines**
- "Show me leads in 'Demos Management' with status 'Follow up 1'"
- "List all people in my Investors group"
- "Find active clients in my Customers group"
- "What groups do I have in Folk?"

## Example Flow

```
User: "I just had coffee with Alex Rivera, she's interested in our API. Remind me to send her docs next week."

AI: find_person("Alex Rivera")
→ {"found": true, "matches": [{"id": "abc123", "name": "Alex Rivera", "email": "alex@techco.io"}]}

AI: add_note("abc123", "Had coffee - interested in API, wants to see docs")
→ {"id": "note456", "added": true}

AI: log_interaction("abc123", "meeting", "2024-01-15T10:00:00Z")
→ {"id": "int789", "logged": true}

AI: set_reminder("abc123", "Send API docs to Alex", "2024-01-22T09:00:00Z")
→ {"id": "rem012", "set": true}

AI: "Done! I've added a note about your coffee chat, logged the meeting, and set a reminder for next Monday to send her the API docs."
```

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest tests/ -v

# Format code
uv run ruff format .

# Lint
uv run ruff check .

# Type check
uv run mypy src/

# Run all checks
make check

# Build bundle for testing
make pack
```

## API Reference

This server uses the [Folk REST API](https://developer.folk.app). Key endpoints:

- Base URL: `https://api.folk.app/v1`
- Authentication: Bearer token
- Rate limits apply (see Folk documentation)

## License

MIT
