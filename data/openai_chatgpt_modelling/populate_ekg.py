import os
from datetime import datetime, timedelta

BASE_DATE = datetime(2026, 1, 1)
START_HOUR = 8
SLOT_MINUTES = 30

# Your original Patient1 events grouped by day
events = {
    1: ["Walking","Diet","FootCare","Stress","Stretching","BSM","BPM",
        "FootInspect","Fatigue","Thirst","ExerciseMgmt","MedMgmt","Consult"],

    2: ["Cycling","HealthyEat","Gardening","SleepMgmt","Strength","BSM",
        "SymTrack","WeightMon","Dizziness","Headache","DietMgmt",
        "HyperMgmt","Advice"],

    3: ["Swimming","Cooking","Mobility","AnxietyMgmt","Walking","BSM",
        "BPM","FoodLog","Numbness","Tingling","WeightMgmt",
        "HypoMgmt","SymDiscuss"],

    4: ["Walking","Strength","TraditionalRecipe","StressMgmt","Indoor",
        "BSM","BPM","MedAdh","JointPain","ColdFeet",
        "ExerciseMgmt","MedMgmt","Education"],

    5: ["Swimming","Chess","Gardening","SleepMgmt","Stretching",
        "BSM","FootInspect","WeightMon","WeightGain","Swelling",
        "DietMgmt","HyperMgmt","AdviceSeek"],

    6: ["Cycling","PlayOud","Mobility","AnxietyMgmt","Walking",
        "BSM","SymTrack","FoodLog","DryMouth","SleepDisturb",
        "WeightMgmt","HypoMgmt","Support"],

    7: ["Walking","Strength","HealthyEat","StressMgmt","Indoor",
        "BSM","BPM","MedAdh","FootPain","Vision",
        "DietMgmt","MedMgmt","Consult"]
}


def main():
    f = open("patient-data.ttl", "w")
    f.write("@prefix : <http://example.org/diabetes#> .\n")
    f.write("@prefix : <http://example.org/diabetes#> .\n")
    f.write("@prefix time: <http://www.w3.org/2006/time#> .\n")
    f.write("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .\n")

    total = 0

    for day, day_events in events.items():

        day_date = BASE_DATE + timedelta(days=day-1)
        current_time = datetime(
            day_date.year, day_date.month, day_date.day, START_HOUR, 0, 0
        )

        for event in day_events:

            total += 1

            event_id = f":P1D{day}_{event}"
            start_id = f"{event_id}_Start"
            end_id = f"{event_id}_End"

            start_time = current_time
            end_time = current_time + timedelta(minutes=SLOT_MINUTES)

            f.write(f"{event_id} a time:ProperInterval ;\n")
            f.write(f"    time:hasBeginning {start_id} ;")
            f.write(f"    time:hasEnd {end_id} .\n")

            f.write(f"{start_id} a time:Instant ;")
            f.write(f"    time:inXSDDateTime \"{start_time.isoformat()}\"^^xsd:dateTime .\n")

            f.write(f"{end_id} a time:Instant ;")
            f.write(f"    time:inXSDDateTime \"{end_time.isoformat()}\"^^xsd:dateTime .\n")

            current_time = end_time
    f.close()

    print(f"# Total intervals generated: {total}")


if __name__ == '__main__':
    main()