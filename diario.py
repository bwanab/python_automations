import glob
import csv

#  files = glob.glob('*.txt')

timeline = []
# for file in files:
    # with open(file, 'r') as f:
    #     reader = csv.reader(f, delimiter='|')
    #     for date, event, comment in reader:
    #         timeline.append((date, event, comment))

with open("/Users/billallen/Documents/Obsidian Vault/diario/events.md", 'r') as f:
    reader = csv.reader(f, delimiter='|')
    i = 0
    for x1, date, event, comment, x2 in reader:
        if i < 2:
            i = i + 1
        else:
            timeline.append((date, event, comment))
            #print(date, event, comment)

from graphviz import Graph

dot = Graph()
for date, event, comment in timeline:
    dot.node(date, event, tooltip=comment)

dot.render('timeline1.gv', format='png', view=True)
