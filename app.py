import gc
import operator
import os
import random

import flask
import objgraph

LEAKY = []
class Leaker(object):
    pass

app = flask.Flask(__name__)
app.secret_key = "it's a secret to everyone"

@app.route('/')
def index():
    # Simulate a "leak" by storing some Leakers in a global.
    for i in range(random.randint(0, 1000)):
        LEAKY.append(Leaker())
    return "drip drip"

@app.route('/mem')
def mem():
    return flask.render_template('mem.html',
        common_types = objgraph.most_common_types(),
        growth = _object_growth(),
    )

def _object_growth():
    """
    Shows changes in allocations, like objgraph.show_growth(), except:

    - show_growth() prints to stdout, which we don't want, so this just returns.
    - this saves the peaks in the session, so that each user sees the changes
      between *their* last page load, not some global.
    - this function is obsessively commented :)

    """

    # We don't want our numbers crudded up by a GC cycle that hasn't run yet,
    # so force GC before we gather stats.
    gc.collect()

    # `typestats() `returns a dict of {type-name: count-of-allocations}. We'll
    # compare the current count for each type to the previous count, stored
    # in the session as `peak_stats`, and save the changes into `deltas`.
    peak_stats = flask.session.get('peak_stats', {})
    stats = objgraph.typestats()
    deltas = {}

    # For each type, look it the old count in `peak_stats`, defaulting to 0.
    # We're really only interested in *growth* -- remember, we're looking for
    # memory leaks -- so if the current count is greater than the peak count,
    # we want to return that change in `deltas` and also note the new peak
    # for later.
    for name, count in stats.iteritems():
        old_count = peak_stats.get(name, 0)
        if count > old_count:
            deltas[name] = count - old_count
            peak_stats[name] = count

    # We have to remember to store `peak_stats` back in the session, otherwise
    # Flask won't notice that it's changed.
    flask.session['peak_stats'] = peak_stats

    # Return (type-name, delta) tuples, sorted by objects with the biggest growth.
    return sorted(deltas.items(), key=operator.itemgetter(1), reverse=True)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
