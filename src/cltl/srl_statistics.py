import json
import words_to_hierarchy as tree
import os

def get_statistics(annotated_conversations):

    activity_dict = {}
    agent_dict = {}
    patient_dict = {}
    instrument_dict = {}
    manner_dict = {}
    location_dict = {}
    time_dict = {}

    for conversation in annotated_conversations:
        if len(conversation) > 0:
            for turn in conversation:
                event = turn['Output']
                if 'activity' in event:
                    activity = event['activity']
                    if activity in activity_dict:
                        activity_dict[activity] += 1
                    else:
                        activity_dict[activity] = 1
                    if 'agent' in event:
                        for agent in event['agent']:
                            if agent in agent_dict:
                                agent_dict[agent] += 1
                            else:
                                agent_dict[agent] = 1
                    if 'patient' in event:
                        for patient in event['patient']:
                            if patient in patient_dict:
                                patient_dict[patient] += 1
                            else:
                                patient_dict[patient] = 1
                    if 'instrument' in event:
                        for instrument in event['instrument']:
                            if instrument in instrument_dict:
                                instrument_dict[instrument] += 1
                            else:
                                instrument_dict[instrument] = 1
                    if 'manner' in event:
                        for manner in event['manner']:
                            if manner in manner_dict:
                                manner_dict[manner] += 1
                            else:
                                manner_dict[manner] = 1
                    if 'location' in event:
                        for location in event['location']:
                            if location in location_dict:
                                location_dict[location] += 1
                            else:
                                location_dict[location] = 1
                    if 'time' in event:
                        for time in event['time']:
                            if time in time_dict:
                                time_dict[time] += 1
                            else:
                                time_dict[time] = 1
    return activity_dict, agent_dict, patient_dict, instrument_dict, manner_dict, location_dict, time_dict

def extract_subclass_relations(dictionary:{}):
    # create a hierarchy for the items in a dictionary by subtyping items
    # based on the similarity with other items such that shorter strings are the parents of longer strings
    words = list(dictionary.keys())
    hierarchy = infer_word_hierarchy(words)
    print(hierarchy)

def main():

    output_dir = "/Users/piek/Desktop/Diabetes/code/event-centric-knowledgegraphs-from-conversations/output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    f = open("/Users/piek/Desktop/Diabetes/load_datasets/diabetes/event_srl.json", "r")
    annotated_conversations = json.load(f)
    print(len(annotated_conversations))
    activity_dict, agent_dict, patient_dict, instrument_dict, manner_dict, location_dict, time_dict = get_statistics(annotated_conversations)

    name = "activities"
    activities = list(activity_dict.keys())
    #G = tree.build_hybrid_tree(activities, k=3)
    G = tree.build_hybrid_tree_with_single_word_parents(activities, k=10)
    tree.draw_tree(G, output_dir, name)

    roots = tree.get_roots(G)
    for root in roots:
        subtree = tree.extract_subtree_with_depth(G, root, max_depth=0)
        label = name+"_"+subtree.nodes[root].get("label")
        tree.draw_tree(subtree, output_dir, label)

    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()

    leaf_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "leaf"]
    cluster_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "cluster"]
    macro_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "macro"]
    depth = tree.get_tree_depth(G, root=None)
    print(name)
    print("Total nodes:", total_nodes)
    print("Leaves:", len(leaf_nodes))
    print("Clusters:", len(cluster_nodes))
    print("Macros:", len(macro_nodes))
    print("Edges:", total_edges)
    print("Average depth:", depth)



if __name__ == '__main__':
    main()