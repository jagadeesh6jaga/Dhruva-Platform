import os

# Metering constants to calculate inference units
ASR_GPU_MULTIPLIER = 1
ASR_CPU_MULTIPLIER = 1
ASR_RAM_MULTIPLIER = 1

NMT_TOKEN_CALCULATION_MULTIPLIER = 1
NMT_GPU_MULTIPLIER = 1
NMT_CPU_MULTIPLIER = 1
NMT_RAM_MULTIPLIER = 1

TTS_GPU_MULTIPLIER = 1
TTS_CPU_MULTIPLIER = 1
TTS_RAM_MULTIPLIER = 1
TTS_TOKEN_CALCULATION_MULTIPLIER = 1

NER_TOKEN_CALCULATION_MULTIPLIER = 1
NER_GPU_MULTIPLIER = 1
NER_CPU_MULTIPLIER = 1
NER_RAM_MULTIPLIER = 1

LOGS_CONTAINER = "logs"
ERROR_CONTAINER = "errors"
FEEDBACK_CONTAINER = "feedback"

LOCAL_DATA_DIR = "./data"

# Create a local directory to hold blob data
os.makedirs(LOCAL_DATA_DIR, exist_ok=True)
