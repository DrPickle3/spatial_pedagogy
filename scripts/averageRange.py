import csv

def average_x(filename):
    values = []

    with open(filename, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            values.append(float(row['x']))

    if values:
        return sum(values) / len(values)
    else:
        return None

if __name__ == "__main__":
    filename = "../logs/positions.csv"  # replace with your CSV file path
    avg = average_x(filename)
    if avg is not None:
        print(f"Average x = {avg:.2f}")
    else:
        print("No data found.")