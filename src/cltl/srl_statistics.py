import json
import words_to_hierarchy as tree
import os

def get_statistics(annotated_conversations, threshold=3):

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
                        if type(event['agent']) == str:
                            event['agent'] = [event['agent']]
                        for agent in event['agent']:
                            if agent in agent_dict:
                                agent_dict[agent] += 1
                            else:
                                agent_dict[agent] = 1
                    if 'patient' in event:
                        if type(event['patient']) == str:
                            event['patient'] = [event['patient']]
                        for patient in event['patient']:
                            if patient in patient_dict:
                                patient_dict[patient] += 1
                            else:
                                patient_dict[patient] = 1
                    if 'instrument' in event:
                        if type(event['instrument']) == str:
                            event['instrument'] = [event['instrument']]
                        for instrument in event['instrument']:
                            if instrument in instrument_dict:
                                instrument_dict[instrument] += 1
                            else:
                                instrument_dict[instrument] = 1
                    if 'manner' in event:
                        if type(event['manner']) == str:
                            event['manner'] = [event['manner']]
                        for manner in event['manner']:
                            if manner in manner_dict:
                                manner_dict[manner] += 1
                            else:
                                manner_dict[manner] = 1
                    if 'location' in event:
                        if type(event['location']) == str:
                            event['location'] = [event['location']]
                        for location in event['location']:
                            if location in location_dict:
                                location_dict[location] += 1
                            else:
                                location_dict[location] = 1
                    if 'time' in event:
                        if type(event['time']) == str:
                            event['time'] = [event['time']]
                        for time in event['time']:
                            if time in time_dict:
                                time_dict[time] += 1
                            else:
                                time_dict[time] = 1

    activity_dict = {k: v for k, v in activity_dict.items() if v >= threshold}
    trimmed_activity_dict = dict(sorted(activity_dict.items(), key=lambda x: x[1], reverse=True))

    agent_dict = {k: v for k, v in agent_dict.items() if v >= threshold}
    trimmed_agent_dict = dict(sorted(agent_dict.items(), key=lambda x: x[1], reverse=True))

    patient_dict = {k: v for k, v in patient_dict.items() if v >= threshold}
    trimmed_patient_dict = dict(sorted(patient_dict.items(), key=lambda x: x[1], reverse=True))

    instrument_dict = {k: v for k, v in instrument_dict.items() if v >= threshold}
    trimmed_instrument_dict = dict(sorted(instrument_dict.items(), key=lambda x: x[1], reverse=True))

    manner_dict = {k: v for k, v in manner_dict.items() if v >= threshold}
    trimmed_manner_dict = dict(sorted(manner_dict.items(), key=lambda x: x[1], reverse=True))

    location_dict = {k: v for k, v in location_dict.items() if v >= threshold}
    trimmed_location_dict = dict(sorted(location_dict.items(), key=lambda x: x[1], reverse=True))

    time_dict = {k: v for k, v in time_dict.items() if v >= threshold}
    trimmed_time_dict = dict(sorted(time_dict.items(), key=lambda x: x[1], reverse=True))

    return trimmed_activity_dict, trimmed_agent_dict, trimmed_patient_dict, trimmed_instrument_dict, trimmed_manner_dict, trimmed_location_dict, trimmed_time_dict

def get_analysis_for_srl_dict(srl_dict, name, output_dir, head_first = True):
    phrases = list(srl_dict.keys())
    print(name)
    print(phrases)
    G = tree.build_hybrid_tree_with_single_word_parents(phrases, k=10, head_first=head_first, labels_as_ids=True)
    total_nodes = G.number_of_nodes()
    total_edges = G.number_of_edges()
    print(name, total_nodes, total_edges)

    leaf_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "leaf"]
    cluster_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "cluster"]
    macro_nodes = [n for n, d in G.nodes(data=True) if d.get("type") == "macro"]
    macro_nodes_depths ={}
    for root in macro_nodes:
        depth = tree.get_tree_depth(G, root)
        macro_nodes_depths.update({G.nodes[root]['label']:depth})

    stats = {"name": name, "Total phrases": len(phrases), "Phrase counts": srl_dict, "Leaf nodes": len(leaf_nodes), "Cluster nodes": len(cluster_nodes), "Macro nodes": len(macro_nodes), "Macro nodes depth": macro_nodes_depths, "Total nodes": total_nodes, "Total edges": total_edges}
    f = open(output_dir+"/"+name+".json", "w")
    json.dump(stats, f, indent=4)
    f.close()

    f = open(output_dir+"/"+name+".ttl", "w")
    triples = tree.get_subtype_relations(G)
    print('Nr of triples: ', len(triples))

    for triple in triples:
        #print(tree.print_parent_child(triple))
        f.write(tree.triple_to_turtle(triple)+"\n")
    f.close()

    f = open(output_dir+"/"+name+"_triples.json", "w")
    json.dump(triples, f, indent=4)
    f.close()

    tree.draw_tree(G, output_dir, name)
    roots = tree.get_roots(G)
    for root in roots:
        subtree = tree.extract_subtree_with_depth(G, root, max_depth=0)
        label = name+"_"+subtree.nodes[root].get("label")
        tree.draw_tree(subtree, output_dir, label)



def main():
    threshold = 1
    output_dir = "/Users/piek/Desktop/Diabetes/code/event-centric-knowledgegraphs-from-conversations/output"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    f = open("/Users/piek/Desktop/Diabetes/load_datasets/diabetes/event_srl.json", "r")
    annotated_conversations = json.load(f)
    print(len(annotated_conversations))
    activity_dict, agent_dict, patient_dict, instrument_dict, manner_dict, location_dict, time_dict = get_statistics(annotated_conversations, threshold=threshold)

    if len(activity_dict)>0:
        get_analysis_for_srl_dict(activity_dict, "activities_"+str(threshold), output_dir, head_first = True)
    if len(agent_dict)>0:
        get_analysis_for_srl_dict(agent_dict, "agents_"+str(threshold), output_dir, head_first=True)
    if len(patient_dict)>0:
        get_analysis_for_srl_dict(patient_dict, "patients_"+str(threshold), output_dir, head_first = True)
    if len(instrument_dict)>0:
        get_analysis_for_srl_dict(instrument_dict, "instruments_"+str(threshold), output_dir, head_first = True)
    if len(manner_dict)>0:
        get_analysis_for_srl_dict(manner_dict, "manners_"+str(threshold), output_dir, head_first = True)
    if len(location_dict)>0:
        get_analysis_for_srl_dict(location_dict, "locations_"+str(threshold), output_dir, head_first = True)
    # if len(time_dict)>0:
    #     get_analysis_for_srl_dict(time_dict, "times_"+str(threshold), output_dir, head_first = True)

if __name__ == '__main__':
    main()