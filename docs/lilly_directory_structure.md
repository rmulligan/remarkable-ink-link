# Lilly Directory Structure

The Claude Penpal service (Lilly) organizes files in a hierarchical directory structure to keep notebook contents well-organized and persistent between service restarts.

## Base Directory

The base directory is configured through the `LILLY_ROOT_DIR` environment variable, which defaults to `~/dev`. Within this base directory, a `Lilly` folder is created to store all notebook-related contents, organized by subject.

```
~/dev/                            # Base directory (configurable via LILLY_ROOT_DIR)
└── Lilly/                        # Main Lilly directory
    ├── claude_conversation_ids.json  # Stored conversation IDs
    ├── General/                  # Default subject directory
    │   ├── Notebook_1/
    │   └── Notebook_2/
    ├── Work/                     # Another subject directory
    │   └── Work_Project/
    └── Personal/                 # Another subject directory
        └── Journal/
```

## Subject Classification

Notebooks are organized into subject directories based on tags in the notebook:

1. Notebooks can be tagged with a subject using a tag of the form `Subject:Name` (e.g., `Subject:Work`, `Subject:Personal`)
2. The "Subject" prefix is configurable via `LILLY_SUBJECT_TAG` environment variable
3. If no subject tag is found, notebooks are placed in the default subject directory (configurable via `LILLY_DEFAULT_SUBJECT`)

## Notebook Directories

Each reMarkable notebook gets its own directory under the appropriate subject folder. The directory name is derived from the notebook's name, with spaces replaced by underscores and any non-alphanumeric characters (except hyphens and underscores) replaced by underscores.

```
~/dev/Lilly/Work/                  # Subject directory
└── Testing_Notebook/              # Notebook directory
    ├── Testing_Notebook.rmdoc     # Downloaded notebook file
    ├── extracted/                 # Extracted notebook contents
    │   ├── page1.content
    │   ├── page1.rm
    │   ├── page2.content
    │   └── page2.rm
    ├── modified_Testing_Notebook_20250514_120000.rmdoc  # Modified notebook with AI response
    └── ...
```

## Conversation Tracking

The service maintains a `claude_conversation_ids.json` file in the Lilly directory to track conversation contexts for each notebook. This allows the service to maintain continuity between interactions with the same notebook.

## Configuration

You can customize the directory structure with the following environment variables:

- `LILLY_ROOT_DIR`: Base directory for storing Lilly-related files (default: `~/dev`)
- `LILLY_TAG`: Tag to look for in notebooks (default: `Lilly`)
- `LILLY_POLLING_INTERVAL`: Interval in seconds to check for tagged notebooks (default: `60`)
- `LILLY_SUBJECT_TAG`: Tag prefix for subject classification (default: `Subject`)
- `LILLY_DEFAULT_SUBJECT`: Default subject when none is specified (default: `General`)
- `LILLY_USE_SUBJECT_DIRS`: Whether to organize by subject (true) or use flat structure (false) (default: `true`)
- `LILLY_PRE_FILTER_TAG`: Document-level tag for pre-filtering notebooks (default: `HasLilly`)

Add these to your `.env` file to change the defaults:

```
# Lilly configuration
LILLY_ROOT_DIR=/path/to/your/preferred/directory
LILLY_TAG=YourPreferredTag
LILLY_POLLING_INTERVAL=30
LILLY_SUBJECT_TAG=Topic
LILLY_DEFAULT_SUBJECT=Misc
LILLY_USE_SUBJECT_DIRS=true
LILLY_PRE_FILTER_TAG=HasLilly
```

## Running the Service

Start the Claude Penpal service with:

```bash
python -m inklink.main penpal
```

Or with custom subject settings:

```bash
python -m inklink.main penpal --subject-tag "Topic" --default-subject "Misc" --use-subject-dirs --pre-filter-tag "HasLilly"
```

The service will:
1. Check for notebooks with pages tagged with "Lilly" (or your custom tag)
2. Download and extract these notebooks to their dedicated directories
3. Process any queries and generate AI responses
4. Upload modified notebooks back to the reMarkable Cloud

## How to Tag Notebooks

To specify a subject for a notebook, add a tag to the notebook or a page:

1. In the reMarkable app, select the notebook or page
2. Click on the tag icon (or add tags feature)
3. Add a tag with the format `Subject:Name` (e.g., `Subject:Work`)

This will cause the notebook to be organized into the corresponding subject directory when processed.

## Manually Inspecting Notebooks

You can manually inspect the downloaded notebooks in their respective directories:

```bash
cd ~/dev/Lilly/Work/Testing_Notebook
ls -la
```

This structure makes it easy to debug issues, recover from failures, and maintain a history of interactions with each notebook.

## Benefits of Subject-Based Organization

- Keeps related notebooks together in logical categories
- Prevents cluttering the main Lilly directory with many notebooks
- Improves organization and searchability
- Allows for context-based management of notebooks

## Performance Optimization with Pre-Filtering

For better performance, especially with many notebooks, the service uses pre-filtering:

1. **HasLilly Tag**: Add a "HasLilly" tag (or customized tag name) to notebooks that contain pages with "Lilly" tags
2. **Pre-filtering**: The service first checks for notebooks with the "HasLilly" tag
3. **Efficient Processing**: Only pre-filtered notebooks are downloaded and checked for page-level tags

This approach reduces the number of notebooks that need to be downloaded and processed in detail, significantly improving performance in large collections of notebooks.

To disable pre-filtering (scan all notebooks):

```bash
python -m inklink.main penpal --no-pre-filter
```