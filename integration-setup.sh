#!/usr/bin/env bash
set -euo pipefail

# Integration Flow Testing Setup Script
# Run this once to set up your environment

echo "=========================================="
echo "Integration Flow Testing - Setup"
echo "=========================================="
echo ""

# Detect Python version
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.10 or later."
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo "✓ Found Python: $PYTHON_VERSION"

# Check Python version (need 3.10+)
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python 3.10 or later required (found $PYTHON_VERSION)"
    exit 1
fi

echo "✓ Python version OK"
echo ""

# Install dependencies
echo "Installing required packages..."
echo ""

# Check if we need tomli (for Python < 3.11)
if [ "$PYTHON_MINOR" -lt 11 ]; then
    echo "  - Installing tomli (TOML parser for Python <3.11)..."
    $PYTHON_CMD -m pip install --break-system-packages tomli pyyaml 2>/dev/null || \
    $PYTHON_CMD -m pip install tomli pyyaml
else
    echo "  - Installing pyyaml (tomllib available in stdlib)..."
    $PYTHON_CMD -m pip install --break-system-packages pyyaml 2>/dev/null || \
    $PYTHON_CMD -m pip install pyyaml
fi

echo ""
echo "✓ Dependencies installed"
echo ""

# Create default config if it doesn't exist
CONFIG_FILE="integration_config.toml"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Creating default configuration: $CONFIG_FILE"
    cat > "$CONFIG_FILE" << 'EOF'
# Integration Flow Testing Configuration
# Edit these values to match your project structure

[paths]
# Where unit ledgers are located
ledgers_root = "./ledgers"

# Where integration flow outputs will be written
integration_output_dir = "./integration-output"

# Optional base subdirectory under ledgers_root (e.g., "resources/ledgers")
ledgers_base_subdir = ""

[discovery]
# Ledger directory structure: "auto" | "flat" | "package"
ledger_structure = "auto"

# Optional namespace anchor to strip when resolving packages
namespace_anchor = ""

[stages]
# Output filenames for each stage (relative to integration_output_dir)
stage1_output = "stage1-integration-points.yaml"
stage2_output = "stage2-classified-points.yaml"
stage3_output = "stage3-integration-graph.yaml"
stage4_output = "stage4-flows.yaml"
stage5_output = "stage5-windows.yaml"

[processing]
# Maximum depth when traversing flows (prevents infinite loops)
max_flow_depth = 20

# Minimum window length for sliding windows
min_window_length = 2

# Maximum window length (0 or null = use full flow length)
max_window_length = 0

# Treat boundary integrations as terminal nodes
boundaries_are_terminal = true

[output_format]
# YAML formatting options
yaml_width = 100
yaml_indent = 2
yaml_sort_keys = false

# Include metadata sections in outputs
include_metadata = true

# Include debug information in outputs
debug_output = false

[logging]
# Verbosity level: 0 (quiet) | 1 (normal) | 2 (verbose)
verbosity = 1

# Show progress bars for long-running operations
show_progress = true

[validation]
# Path to JSON schema file
schema_path = "./integration/specs/integration-flow-schema.json"

# Validate outputs against schema
validate_outputs = true
EOF
    echo "✓ Created: $CONFIG_FILE"
else
    echo "✓ Configuration file already exists: $CONFIG_FILE"
fi

echo ""

# Create output directory
OUTPUT_DIR="./integration-output"
if [ ! -d "$OUTPUT_DIR" ]; then
    mkdir -p "$OUTPUT_DIR"
    echo "✓ Created output directory: $OUTPUT_DIR"
else
    echo "✓ Output directory exists: $OUTPUT_DIR"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "  1. Review configuration:"
echo "     \$ cat $CONFIG_FILE"
echo ""
echo "  2. Adjust paths if needed (edit $CONFIG_FILE)"
echo ""
echo "  3. Run Stage 1 to collect integration points:"
echo "     \$ ./stage1_collect_integration_points.py"
echo ""
echo "  4. Or run the full pipeline:"
echo "     \$ ./integration_flow_pipeline.py"
echo ""
echo "For help on any stage:"
echo "  \$ ./stage1_collect_integration_points.py --help"
echo ""