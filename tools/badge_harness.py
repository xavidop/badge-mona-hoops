import sys; sys.path.insert(0, '/state'); import kit, time
g, update = kit.load('/state/dev_hoops', 'mona_hoops')
cost, raw = kit.step(update); kit.shot('title', raw, cost)
kit.step(update, (BUTTON_SELECT,)); kit.step(update)
def shoot(power_target, angle_index, label):
    g['angle_index'] = angle_index
    # hold Select until the meter passes the target on the way up, then release
    ok, raw, cost = kit.run_until(update, lambda: g['power'] >= power_target, 1500, (BUTTON_SELECT,))
    _, avg, raw = kit.run_for(update, 1, (BUTTON_SELECT,)); kit.shot(label + ' charging', raw, avg)
    kit.step(update)   # release
    before = g['score']
    ok, raw, cost = kit.run_until(update, lambda: g['ball'] is not None and g['ball'][1] < g['RIM_Y'] - 20 and g['ball'][0] > g['SPOTS'][0], 2000)
    kit.shot(label + ' in flight', raw, cost)
    ok, raw, cost = kit.run_until(update, lambda: g['ball'] is None, 4000)
    print('  ', label, 'power %.2f angle %d -> score %d (+%d) msg %s streak %d spot %d' % (power_target, g['ANGLES'][angle_index], g['score'], g['score'] - before, g['message'], g['streak'], g['spot']))
    return g['score'] - before
# sweep a few powers to find makes from the first spot, then play on
results = []
for p, a in ((0.45, 4), (0.55, 4), (0.65, 4), (0.75, 4), (0.85, 4), (0.5, 5), (0.6, 5), (0.7, 5), (0.8, 5), (0.6, 3), (0.7, 3), (0.8, 3)):
    results.append((p, a, shoot(p, a, 'shot')))
print('sweep:', results)
g['started_at'] = badge.ticks - g['GAME_MS'] + 1500
_, avg, raw = kit.run_for(update, 200); kit.shot('last seconds', raw, avg)
ok, raw, cost = kit.run_until(update, lambda: g['mode'] == g['RESULT'], 4000)
_, avg, raw = kit.run_for(update, 300); kit.shot('result screen', raw, avg)
g['on_exit'](); print('DONE hoops state', g['state'])
