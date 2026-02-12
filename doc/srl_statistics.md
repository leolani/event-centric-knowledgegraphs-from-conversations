# SRL Statistics (srl_statistics.py)

This module provides functionality for analyzing and visualizing semantic role labeling (SRL) statistics from annotated conversations. It generates hierarchical tree structures and statistical analysis for different semantic roles.

## Dependencies

- json
- words_to_hierarchy
- os

## Core Functions

### get_statistics(annotated_conversations, threshold=3)
Processes annotated conversations to generate frequency statistics for different semantic roles.

**Parameters:**
- `annotated_conversations`: List of annotated conversation turns
- `threshold`: Minimum frequency threshold for including items (default: 3)

**Returns:**
Seven dictionaries containing frequency counts for:
- Activities
- Agents
- Patients
- Instruments
- Manners
- Locations
- Time expressions

### get_analysis_for_srl_dict(srl_dict, name, output_dir)
Generates hierarchical tree analysis and visualization for a semantic role dictionary.

**Parameters:**
- `srl_dict`: Dictionary containing semantic role elements and their frequencies
- `name`: Name prefix for output files
- `output_dir`: Directory where output files will be saved

**Outputs:**
1. JSON file with statistics including:
   - Total number of phrases
   - Phrase frequency counts
   - Node counts (leaf, cluster, macro)
   - Tree depth information
   - Total nodes and edges
2. Tree visualizations:
   - Main tree diagram
   - Individual subtree diagrams

## Main Function

### main()
Entry point that:
1. Sets up output directory
2. Loads annotated conversations
3. Generates statistics with specified threshold
4. Creates analysis and visualizations for each semantic role type

## Output Files

The module generates several types of output files in the specified directory:
1. JSON files containing statistics for each semantic role
2. PNG files with tree visualizations:
   - Complete hierarchy for each semantic role
   - Individual subtree visualizations for macro clusters

## Usage Example



## Notes

- Uses hierarchical clustering to organize semantic role elements
- Generates both statistical analysis and visual representations
- Supports threshold-based filtering to focus on frequent patterns
- Integrates with words_to_hierarchy module for tree construction
