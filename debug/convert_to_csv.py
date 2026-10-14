import re
import csv

log_file = "debug_pipeline_20251003_012808.log"
csv_file = "logfile_clean_20251003_012808.csv"

# Pattern to detect start of log entries
entry_start_re = re.compile(r'^(\d{4}-\d{2}-\d{2} at \d{2}:\d{2}:\d{2}) \| (\w+) \| (.*?):(.*?):(\d+) - (.*)$')

entries = []

with open(log_file, encoding='utf-8') as f:
    current_entry = None
    in_prompt_block = False

    for line in f:
        line = line.rstrip('\n')
        if not line.strip():
            continue  # skip blank lines

        m = entry_start_re.match(line)
        if m:
            # Save previous entry
            if current_entry:
                entries.append(current_entry)

            timestamp, level, module, func, lineno, message = m.groups()

            # Detect start of a prompt block
            if "Prompt built for" in message or "Prompt built for WEM" in message:
                message = "[GENERATED PROMPT LOGGED ELSEWHERE]"
                in_prompt_block = True
            else:
                in_prompt_block = False

            current_entry = [timestamp, level, module, func, lineno, message]
        else:
            # Continuation of previous entry
            if in_prompt_block:
                # skip all lines in prompt block
                continue
            else:
                current_entry[5] += "\n" + line

    # add last entry
    if current_entry:
        entries.append(current_entry)

# write CSV
with open(csv_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.writer(f)
    writer.writerow(["Timestamp","Level","Module","Function","LineNo","Message"])
    writer.writerows(entries)
