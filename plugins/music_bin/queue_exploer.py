def queue_expr(PriorityQueue_):
    a =[]
    for i in PriorityQueue_ :
        a.append(i.item)
    return a

class Prioritize:
        def __init__(self, priority, item):
            self.priority = priority
            self.item = item

        def __eq__(self, other):
            return self.priority == other.priority

        def __lt__(self, other):
            return self.priority < other.priority