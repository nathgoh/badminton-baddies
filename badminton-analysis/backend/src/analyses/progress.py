ANALYZING_PROGRESS_STEPS: list[tuple[int, str]] = [
    (12, "Ingesting the YouTube match and normalizing the video."),
    (24, "Extracting the setup frame from the opening rally window."),
    (36, "Detecting court geometry and applying any saved manual overrides."),
    (48, "Detecting players and building multi-person tracks."),
    (58, "Assigning the selected player to the tracked movement sequence."),
    (69, "Extracting pose landmarks and movement signals."),
    (80, "Inferring shot events from the tracked rally sequence."),
    (91, "Scoring tactical shot quality and decision outcomes."),
    (98, "Assembling the coach report and analytics evidence."),
]
