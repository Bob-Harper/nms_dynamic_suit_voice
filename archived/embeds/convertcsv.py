import csv

with open("metadata.csv", encoding="utf-8") as infile, \
     open("output.csv", "w", newline="", encoding="utf-8") as outfile:
    # autodetect delimiter
    sample = infile.read(2048)
    infile.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters="|,;¦\t")
    reader = csv.reader(infile, dialect)
    writer = csv.writer(outfile)

    for row in reader:
        if len(row) < 2:
            continue
        filename, text = row[0], row[1]

        # force sentence case
        sentences = [s.strip().capitalize() for s in text.lower().split(".") if s.strip()]
        fixed_text = ". ".join(sentences) + "."

        writer.writerow([filename, fixed_text])
