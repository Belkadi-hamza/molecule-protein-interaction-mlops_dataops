SHARED_COLUMNS = [
    "target_name",
    "inhibitor_name",
    "monomer_id",
    "affinity_type",
    "affinity_value",
    "affinity_value_display",
    "affinity_strength",
    "reactant_set_id",
    "source_organism",
]

TARGET_COLUMN = "affinity_strength"
CATEGORICAL_COLUMNS = [
    "target_name",
    "inhibitor_name",
    "affinity_type",
    "affinity_value_display",
    "source_organism",
]
NUMERIC_COLUMNS = ["monomer_id", "affinity_value", "reactant_set_id"]
FEATURE_TABLE = "training_features"
RAW_TABLE = "molecule_interactions"