#!/usr/bin/env bash

# GitHub PR Review Script
# This script extracts insights from pull requests using GitHub CLI

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Please install it from https://cli.github.com/"
    exit 1
fi

# Check if user is authenticated with GitHub CLI
if ! gh auth status &> /dev/null; then
    echo "Error: You are not authenticated with GitHub CLI."
    echo "Please run 'gh auth login' to authenticate."
    exit 1
fi

# Default values
REPO=""
AUTHOR=""
ASSIGNEE=""
LABEL=""
STATE="open"
FORMAT="table"
SHOW_COMMENTS=false
SHOW_DETAILS=false
LIMIT=10

# Function to display usage information
show_usage() {
    echo "Usage: $0 [options]"
    echo
    echo "Options:"
    echo "  -r, --repo OWNER/REPO    Specify the repository (default: current repository)"
    echo "  -a, --author USERNAME    Filter PRs by author"
    echo "  -s, --assignee USERNAME  Filter PRs by assignee"
    echo "  -l, --label LABEL        Filter PRs by label"
    echo "  -t, --state STATE        Filter by state: open, closed, merged, all (default: open)"
    echo "  -f, --format FORMAT      Output format: table, json (default: table)"
    echo "  -c, --comments           Show PR comments"
    echo "  -d, --details            Show PR details (description, reviewers, etc.)"
    echo "  -n, --limit NUMBER       Limit the number of PRs shown (default: 10, use 0 for all)"
    echo "  -h, --help               Show this help message"
    echo
    echo "Examples:"
    echo "  $0 -r owner/repo -a username -c"
    echo "  $0 --repo owner/repo --state closed --limit 5"
    echo "  $0 --comments --details"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--repo)
            REPO="$2"
            shift 2
            ;;
        -a|--author)
            AUTHOR="$2"
            shift 2
            ;;
        -s|--assignee)
            ASSIGNEE="$2"
            shift 2
            ;;
        -l|--label)
            LABEL="$2"
            shift 2
            ;;
        -t|--state)
            STATE="$2"
            shift 2
            ;;
        -f|--format)
            FORMAT="$2"
            shift 2
            ;;
        -c|--comments)
            SHOW_COMMENTS=true
            shift
            ;;
        -d|--details)
            SHOW_DETAILS=true
            shift
            ;;
        -n|--limit)
            LIMIT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option $1"
            show_usage
            exit 1
            ;;
    esac
done

# Build the gh pr list command
PR_LIST_CMD="gh pr list"

if [ -n "$REPO" ]; then
    PR_LIST_CMD="$PR_LIST_CMD --repo $REPO"
fi

if [ -n "$AUTHOR" ]; then
    PR_LIST_CMD="$PR_LIST_CMD --author $AUTHOR"
fi

if [ -n "$ASSIGNEE" ]; then
    PR_LIST_CMD="$PR_LIST_CMD --assignee $ASSIGNEE"
fi

if [ -n "$LABEL" ]; then
    PR_LIST_CMD="$PR_LIST_CMD --label $LABEL"
fi

if [ "$STATE" != "open" ]; then
    PR_LIST_CMD="$PR_LIST_CMD --state $STATE"
fi

if [ "$LIMIT" -gt 0 ]; then
    PR_LIST_CMD="$PR_LIST_CMD --limit $LIMIT"
fi

# Add JSON format if needed
if [ "$FORMAT" = "json" ]; then
    PR_LIST_CMD="$PR_LIST_CMD --json number,title,url,author,createdAt,updatedAt,state"
fi

# Function to extract PR insights
extract_pr_insights() {
    local pr_numbers=()
    
    echo "Fetching pull requests..."
    
    if [ "$FORMAT" = "json" ]; then
        eval "$PR_LIST_CMD"
        return
    fi
    
    # Get PR numbers and display the list
    while read -r line; do
        if [[ $line =~ ^#([0-9]+) ]]; then
            pr_number="${BASH_REMATCH[1]}"
            pr_numbers+=("$pr_number")
            echo "$line"
        fi
    done < <(eval "$PR_LIST_CMD")
    
    if [ ${#pr_numbers[@]} -eq 0 ]; then
        echo "No pull requests found matching the criteria."
        return
    fi
    
    # Show details and comments if requested
    if [ "$SHOW_DETAILS" = true ] || [ "$SHOW_COMMENTS" = true ]; then
        echo
        echo "Fetching additional information for each PR..."
        echo
        
        for pr_number in "${pr_numbers[@]}"; do
            echo "================================================================================"
            echo "PR #$pr_number"
            echo "================================================================================"
            
            # Show PR details
            if [ "$SHOW_DETAILS" = true ]; then
                echo
                echo "DETAILS:"
                echo "--------"
                if [ -n "$REPO" ]; then
                    gh pr view "$pr_number" --repo "$REPO"
                else
                    gh pr view "$pr_number"
                fi
                echo
            fi
            
            # Show PR comments
            if [ "$SHOW_COMMENTS" = true ]; then
                echo
                echo "COMMENTS:"
                echo "---------"
                if [ -n "$REPO" ]; then
                    gh pr view "$pr_number" --repo "$REPO" --comments
                else
                    gh pr view "$pr_number" --comments
                fi
                echo
            fi
        done
    fi
}

# Function to generate a summary report
generate_summary_report() {
    echo
    echo "SUMMARY REPORT"
    echo "=============="
    
    # Get PR statistics
    local stats_cmd="gh pr list"
    
    if [ -n "$REPO" ]; then
        stats_cmd="$stats_cmd --repo $REPO"
    fi
    
    stats_cmd="$stats_cmd --json author,createdAt,additions,deletions,state --limit 100"
    
    # Use jq to analyze the data if available
    if command -v jq &> /dev/null; then
        local json_data=$(eval "$stats_cmd")
        
        # Count PRs by author
        echo "PRs by Author:"
        echo "$json_data" | jq -r '.[] | .author.login' | sort | uniq -c | sort -nr | 
            awk '{printf "  %-20s %s\n", $2, $1}'
        
        echo
        
        # Count PRs by state
        echo "PRs by State:"
        echo "$json_data" | jq -r '.[] | .state' | sort | uniq -c | sort -nr | 
            awk '{printf "  %-20s %s\n", $2, $1}'
        
        echo
        
        # Calculate average code changes
        echo "Average Code Changes:"
        echo "$json_data" | jq -r '.[] | [.additions, .deletions] | @tsv' | 
            awk '{ additions += $1; deletions += $2; count++ } 
                 END { 
                   if (count > 0) {
                     printf "  Additions: %.1f per PR\n", additions/count;
                     printf "  Deletions: %.1f per PR\n", deletions/count;
                     printf "  Total: %.1f lines per PR\n", (additions+deletions)/count;
                   } else {
                     print "  No data available";
                   }
                 }'
    else
        echo "Install jq for more detailed statistics."
    fi
}

# Main execution
extract_pr_insights

# Generate summary report if showing details
if [ "$SHOW_DETAILS" = true ]; then
    generate_summary_report
fi

echo
echo "Done!"
