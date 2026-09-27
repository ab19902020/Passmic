"""Episode 1 - "International Break Emergency": staging.

Built from the production sheets' storyboard: Mark alone at his desk, Gary
arrives from the right and sits, Roy walks in through the door (seen from
behind the desk), the three of them "fix" United, Roy leaves.

Every line comes from script.py; a line with no recording yet (Roy's, GN_09)
gets a silent slot of the right length and a mouth that still moves. Drop
series/ep01/audio/RK_nn.mp3 (or .wav) in and re-render: timing and lip sync
pick the recording up automatically.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'ep'))
import script as S                    # noqa: E402
import epengine as E                    # noqa: E402

S.LOUD = set()        # the delivery is played straight: no line is shouted (CAPS words get a nod instead)

# ------------------------------------------------------------------ cameras
FA_WIDE = (0, 0, 1672)
FA_TWO = (400, 190, 1130)
SW_THREE = (300, 150, 1080)
SW_WIDE = (0, 0, 1672)
RV_WIDE = (0, 0, 1672)


def seat_face(bg, who):
    import json
    cfg = json.load(open(os.path.join(HERE, 'backgrounds', bg + '.json')))
    s = cfg['seats'][who]
    return s['face'][0], s['face'][1], s['face_w']


def single(bg, who, frac, xpos):
    """Framing with the face `frac` of the frame width, at `xpos` across."""
    fx, fy, fw = seat_face(bg, who)
    w = fw / frac
    h = w * 9 / 16
    return (fx - xpos * w, fy - 0.40 * h, w)


def roy_frame(frac, xpos=0.5, spot='roy_stand'):
    import json
    cfg = json.load(open(os.path.join(HERE, 'backgrounds', 'reverse.json')))
    sp = cfg['spots'][spot]
    fw = sp['face_w']
    fx = sp['feet'][0]
    fy = sp['feet'][1] - 3.85 * fw           # Roy's standing drawings: eyes 3.85 head widths above the feet
    w = fw / frac
    h = w * 9 / 16
    return (fx - xpos * w, fy - 0.38 * h, w)


M_MED = single('front_a', 'mark', 0.15, 0.42)
M_CU = single('front_a', 'mark', 0.32, 0.45)
G_MED = single('front_a', 'gary', 0.15, 0.58)
G_CU = single('front_a', 'gary', 0.32, 0.55)
R_MED = roy_frame(0.13)
R_CU = roy_frame(0.22)
R_TIGHT = roy_frame(0.34)                # the snap-in for 'Definitely no.'
R_DOOR = roy_frame(0.16, spot='roy_door')

SHOTS = {
    'W': ('front_a', FA_WIDE, {}), '2': ('front_a', FA_TWO, {}),
    # singles show only their subject: the other presenter would be just a stray hand at the frame edge
    'M': ('front_a', M_MED, dict(dof=2.0, order=('mark',))), 'Mc': ('front_a', M_CU, dict(dof=5.0, order=('mark',))),
    'G': ('front_a', G_MED, dict(dof=2.0, order=('gary',))), 'Gc': ('front_a', G_CU, dict(dof=5.0, order=('gary',))),
    'SW': ('wide', SW_THREE, {}), 'SWf': ('wide', SW_WIDE, {}),
    'R': ('reverse', R_MED, dict(dof=2.5, order=('roy',))), 'Rc': ('reverse', R_CU, dict(dof=6.0, order=('roy',))),
    'Rx': ('reverse', R_TIGHT, dict(dof=8.0, order=('roy',))),
    'RW': ('reverse', RV_WIDE, {}), 'RD': ('reverse', R_DOOR, dict(dof=3.0)),
    'B': ('board', None, {}), 'END': ('endcard', None, {}),
}

# ------------------------------------------------------------------ staging
# line id -> (shot, body pose, CU face, [(word, change)...])
# change: 'Mc'/'M'/... cuts the camera at that word; 'body=...'/'face=...' swaps a drawing
P = dict
STAGE = {
    # Mark. Faces follow the delivery tags in script.DELIVERY and stay mostly serious: the
    # close-up drawings mainly set the brows and eyes; the mouth is always the lip sync.
    'MG_01': ('M', 'arms_down', 'angry_rant', [('absolutely', 'body=both_hands_out'), ("it's", 'Mc'),       # frustrated
                                               ('technically', 'M'), ('technically', 'body=shrug'), ('nobody', 'Mc')]),
    'MG_02': ('M', 'arms_down', 'sad', [('checked', 'Mc'), ('checked', 'face=neutral')]),                   # sigh
    'MG_03': ('M', 'both_hands_out', 'angry_rant', [('go', 'Mc'), ('go', 'face=sad'), ("that's", 'M'),       # frustrated
                                                    ("that's", 'body=shrug')]),
    'GN_01': ('2', 'both_hands_out', 'neutral', [('gives', 'G'), ('gives', 'body=arms_down')]),            # calm
    'MG_04': ('M', 'arms_down', 'neutral', [('stock', 'Mc')]),                                              # dry
    'GN_02': ('G', 'both_hands_out', 'neutral', []),                                                        # serious
    'MG_05': ('M', 'pointing', 'smug', [('do', 'Mc')]),                                                     # confident
    'MG_06': ('M', 'both_hands_out', 'neutral', [('players', 'Mc'), ('simple', '2')]),                      # matter-of-fact
    'GN_03': ('Gc', 'arms_down', 'confused', []),                                                           # dry
    'MG_07': ('M', 'both_hands_out', 'neutral', [('cup', 'body=shrug'), ('water', 'Mc')]),                  # explaining
    'GN_04': ('Gc', 'arms_down', 'neutral', []),                                                            # deadpan
    'MG_08': ('M', 'arms_down', 'neutral', [("we've", 'Mc')]),                                              # deadpan
    'GN_05': ('G', 'arms_down', 'neutral', []),                                                             # serious
    'GN_06': ('Gc', 'arms_down', 'head/three_quarter', []),                                                 # firm
    'MG_09': ('Mc', 'arms_down', 'smug', [('somebody', 'M'), ('somebody', 'body=holding_phone'),            # sarcastic
                                          ("gary's", 'Mc')]),
    'GN_07': ('Gc', 'arms_down', 'angry_rant', []),                                                         # firmer
    'GN_08': ('G', 'pointing', 'neutral', []),                                                              # serious
    'GN_09': ('2', 'both_hands_out', 'neutral', []),                                                        # measured
    'GN_10': ('G', 'both_hands_out', 'neutral', [('people', 'Gc')]),                                        # earnest
    'RK_01': ('R', 'arms_crossed', 'neutral', []),          # deadpan
    'MG_10': ('SW', 'both_hands_out', 'shocked', []),                                                       # energised
    'RK_02': ('Rc', 'arms_crossed', 'dry_humour', []),      # dry
    'RK_03': ('R', 'arms_crossed', 'neutral', []),          # flat
    'RK_04': ('Rc', 'arms_crossed', 'dry_humour', []),      # deadpan
    'GN_11': ('G', 'both_hands_out', 'confused', []),                                                       # mildly annoyed
    'MG_11': ('M', 'both_hands_out', 'confused', [('first', 'Mc')]),                                        # curious
    'RK_05': ('Rc', 'palm_down', 'neutral', []),            # matter-of-fact
    'MG_12': ('M', 'pointing', 'neutral', []),                                                              # insistent
    'RK_06': ('Rc', 'palm_down', 'angry', []),              # firm
    'RK_07': ('R', 'arms_crossed', 'sarcastic', []),        # dry
    'RK_08': ('Rc', 'arms_crossed', 'disgust', []),         # dismissive
    'GN_12': ('G', 'pointing', 'neutral', []),                                                              # insistent
    'RK_09': ('Rc', 'pointing', 'neutral', []),             # deadpan
    'GN_13': ('Gc', 'arms_down', 'angry_rant', []),                                                         # defensive
    'RK_10': ('Rc', 'arms_crossed', 'sarcastic', []),       # dry
    'GN_14': ('Gc', 'arms_down', 'sad', []),                                                                # awkward
    'GN_15': ('G', 'both_hands_out', 'sad', []),                                                            # more defensive
    'MG_13': ('M', 'both_hands_out', 'smug', []),                                                           # confident
    'MG_14': ('M', 'pointing', 'neutral', []),                                                              # matter-of-fact
    'MG_15': ('M', 'pointing', 'neutral', []),                                                              # matter-of-fact
    'MG_16': ('Mc', 'arms_down', 'smug', []),                                                               # confident
    'MG_17': ('Mc', 'arms_down', 'confused', []),                                                           # confused
    'GN_16': ('Gc', 'arms_down', 'neutral', []),                                                            # matter-of-fact
    'RK_11': ('Rc', 'pointing', 'neutral', []),             # matter-of-fact
    'MG_18': ('M', 'both_hands_out', 'angry_rant', [('explaining', 'Mc')]),                                 # defensive
    'GN_17': ('G', 'arms_down', 'neutral', []),                                                             # dry
    'MG_19': ('Mc', 'arms_down', 'smug', []),                                                               # smug
    'RK_12': ('Rc', 'arms_crossed', 'dry_humour', []),      # flat
    'MG_20': ('Mc', 'arms_down', 'confused', [('work', 'face=smug')]),                                      # realising
    'RK_13': ('R', 'palm_down', 'neutral', []),             # firm
    'MG_21': ('M', 'both_hands_out', 'smug', [('gary', 'body=pointing'), ('me', 'Mc')]),                    # building excitement
    'RK_14': ('Rc', 'palm_down', 'angry', []),              # firmer
    'GN_18': ('Gc', 'arms_down', 'angry_rant', []),                                                         # firm
    'MG_22': ('Mc', 'arms_down', 'neutral', []),                                                            # matter-of-fact
    'RK_15': ('Rx', 'palm_down', 'angry', []),              # very firm
    'GN_19': ('Gc', 'arms_down', 'confused', []),                                                           # confused
    'MG_23': ('M', 'arms_down', 'neutral', []),                                                             # deadpan
    'GN_20': ('G', 'both_hands_out', 'angry_rant', []),                                                     # exasperated
    'MG_24': ('M', 'pointing', 'smug', []),                                                                 # confident
    'RK_16': ('SW', 'arms_crossed', 'annoyed', []),         # annoyed
    'GN_21': ('2', 'both_hands_out', 'neutral', []),                                                        # serious
    'MG_25': ('M', 'pointing', 'neutral', [('striker', 'Mc')]),                                             # businesslike
    'RK_17': ('R', 'pointing', 'neutral', []),              # matter-of-fact
    'MG_26': ('Mc', 'arms_down', 'angry_rant', []),                                                         # frustrated
    'RK_18': ('Rc', 'arms_crossed', 'neutral', []),         # flat
    'RK_19': ('Rc', 'arms_crossed', 'dry_humour', []),      # dry
    'GN_22': ('G', 'arms_down', 'neutral', []),                                                             # measured
    'GN_23': ('G', 'both_hands_out', 'neutral', []),                                                        # earnest
    'RK_20': ('Rc', 'arms_crossed', 'confused', []),        # confused
    'RK_21': ('R', 'open_hand', 'neutral', []),             # deadpan
    'GN_24': ('Gc', 'arms_down', 'angry_rant', []),                                                         # defensive
    'MG_27': ('M', 'pointing', 'neutral', [('player', 'Mc')]),                                              # earnest
    'MG_28': ('M', 'shrug', 'neutral', [('sounds', 'Mc')]),                                                 # dry
    'GN_25': ('G', 'both_hands_out', 'neutral', [('understanding', 'Gc'), ('understanding', 'face=head/three_quarter')]),  # nostalgic
    'RK_22': ('Rc', 'open_hand', 'sarcastic', []),          # dry
    'GN_26': ('Gc', 'arms_down', 'angry_rant', []),                                                         # warning
    'RK_23': ('R', 'pointing', 'angry', []),                # firm
    'GN_27': ('G', 'both_hands_out', 'neutral', []),                                                        # annoyed
    'GN_28': ('G', 'shrug', 'neutral', [('everybody', 'B')]),                                               # exasperated
    'GN_29': ('G', 'pointing', 'angry_rant', [('board', 'B')]),                                             # frustrated
    'RK_24': ('R', 'arms_crossed', 'annoyed', []),          # finished
    'MG_29': ('2', 'arms_down', 'smug', [('someone', 'Mc'), ('someone', 'face=head/front')]),               # satisfied
    'RK_25': ('RD', 'arms_crossed', 'neutral', []),         # deadpan
    'RK_26': ('RD', 'arms_crossed', 'dry_humour', []),      # dry
}
# a silent reaction shot held after a line: line id -> (shot, who, face)
REACT = {
    'MG_08': ('Gc', 'gary', 'neutral'),
    'RK_04': ('Gc', 'gary', 'sad'),             # "Doesn't make you interesting."
    'RK_08': ('Mc', 'mark', 'sad'),             # "Stupid hypothetical."
    'RK_09': ('Gc', 'gary', 'sad'),             # "...you couldn't build a shed."
    'MG_16': ('Gc', 'gary', 'confused'),        # "...and final say on transfers."
    'RK_11': ('Mc', 'mark', 'shocked'),         # "You've never run one either."
    'RK_12': ('Mc', 'mark', 'confused'),        # "Even worse."
    'MG_22': ('Gc', 'gary', 'confused'),        # "I'm chairman."
    'RK_16': ('2', None, None),                 # "You're all talking rubbish."
    'RK_22': ('Gc', 'gary', 'confused'),        # "...a philosophy to have breakfast."
}
# a deadpan beat before a line: the cut to the speaker comes first, the line after the pause
BEAT = {
    'RK_02': 0.35, 'RK_04': 0.55, 'RK_06': 0.3, 'RK_07': 0.35, 'RK_08': 0.45, 'RK_10': 0.5, 'RK_12': 0.5,
    'RK_14': 0.3, 'RK_15': 0.4, 'RK_16': 0.5, 'RK_18': 0.55, 'RK_22': 0.4, 'RK_25': 0.6, 'RK_26': 0.45,
    'MG_09': 0.3, 'MG_19': 0.35, 'MG_22': 0.4, 'MG_23': 0.35, 'MG_28': 0.3, 'GN_04': 0.3, 'GN_07': 0.35,
    'GN_14': 0.3,
}
REACT_HOLD = 0.9
BOARD_AFTER = {'MG_25': 1.3, 'RK_18': 1.1, 'MG_27': 1.2}


def word_time(ln, word, nth=1):
    k = 0
    for w in ln['words']:
        if w['word'].split('(')[0] == word.lower():
            k += 1
            if k == nth:
                return ln['start'] + w['t0']
    return None


def perform(tl, ln):
    """The delivery on top of the lip sync: a small nod on each CAPS word, eyes
    closed through a [sigh], and a blink in each written pause."""
    who, lid, t_line = ln['who'], ln['id'], ln['start']
    words = ln['words']
    caps = S.emphasised(lid)
    for w in words:
        name = w['word'].split('(')[0]
        if name in caps:
            caps.remove(name)
            t0, t1 = t_line + w['t0'], t_line + w['t1']
            tl.key(t0 - 0.1, who, nod=0.0)
            tl.key(t0 + 0.08, who, nod=1.0, e='ease')
            tl.key(max(t1, t0 + 0.2) + 0.12, who, nod=0.0, e='ease')
    if S.tag(lid) == 'sigh' and words and words[0]['t0'] > 0.3:
        a, b = t_line + 0.04, t_line + words[0]['t0'] - 0.06
        tl.key(a, who, eyes_shut=True)
        tl.key(b, who, eyes_shut=False)
        tl.key(a, who, nod=0.0)
        tl.key((a + b) / 2, who, nod=0.8, e='ease')
        tl.key(b + 0.15, who, nod=0.0, e='ease')
    for w0, w1 in zip(words, words[1:]):
        if w1['t0'] - w0['t1'] > 0.3:
            tl.blinks.setdefault(who, []).append(t_line + (w0['t1'] + w1['t0']) / 2 - 0.05)


def build():
    E.load_alignment()
    tl = E.Timeline(S)
    key, shot = tl.key, tl.shot

    def cut(t, code, **kw):
        bg, rect, extra = SHOTS[code]
        shot(t, bg, rect, **dict(extra, **kw))

    # everyone's starting state
    key(0, 'mark', loc='seat', body='upper/arms_down', face='expressions/neutral', flip=False)
    key(0, 'gary', loc='off', flip=True, body='upper/arms_down', face='expressions/neutral')
    key(0, 'roy', loc='off', body='body/arms_crossed', face='expressions/neutral', flip=False)
    key(0, 'world', fade=1.0)
    key(0.5, 'world', fade=0.0, e='ease')
    cut(0, 'W')
    tl.wait(1.4)

    # board state (what's written up so far), keyed on the 'board' track
    board = []

    def board_add(t, item):
        board.append(item)
        key(t, 'board', items=tuple(board))
        tl.sfx(t, 'marker', 0.7)

    last_code = None
    for item in S.ORDER:
        if item == '@gary_enters':
            t = tl.wait(0.0)
            cut(t, 'W')
            key(t, 'gary', loc='walk', path=('gary_enter_from', 'gary_stand'), u=0.0, flip=True,
                cycle=['body/walk_1', 'body/walk_2', 'body/walk_3', 'body/walk_3b', 'body/walk_4'])
            key(t + 2.3, 'gary', u=1.0, e='linear')
            key(t + 2.3, 'gary', loc='seat', body='upper/arms_down', dy=-0.42)
            key(t + 2.65, 'gary', dy=0.0, e='ease')
            key(t + 0.3, 'mark', face='expressions/confused')
            tl.sfx(t + 2.4, 'chair_creak', 0.9)
            tl.wait(3.0)
            last_code = 'W'
            continue
        if item == '@roy_enters':
            t = tl.wait(0.2)
            cut(t, 'RW')
            tl.sfx(t, 'door_open', 1.0)
            key(t, 'roy', loc='walk', path=('roy_door', 'roy_stand'), u=0.0, flip=True,
                cycle=['body/walk_1', 'body/walk_2', 'body/walk_3', 'body/walk_3b', 'body/walk_4'])
            key(t + 2.6, 'roy', u=1.0, e='linear')
            key(t + 2.6, 'roy', loc='stand', path=('roy_stand', 'roy_stand'), body='body/arms_crossed', flip=False)
            tl.wait(3.3)
            last_code = 'RW'
            continue
        if item == '@board':
            t = tl.wait(0.1)
            cut(t, 'B')
            board_add(t + 0.25, 'title')
            tl.wait(1.6)
            last_code = 'B'
            continue
        if item == '@roy_heads_out':
            t = tl.wait(0.0)
            cut(t, 'RW')
            key(t, 'roy', loc='walk', path=('roy_stand', 'roy_door'), u=0.0, flip=False,
                cycle=['body/walk_1', 'body/walk_2', 'body/walk_3', 'body/walk_3b', 'body/walk_4'])
            key(t + 2.2, 'roy', u=1.0, e='linear')
            key(t + 2.2, 'roy', loc='stand', path=('roy_door', 'roy_door'), body='body/arms_crossed', flip=False)
            tl.wait(2.4)
            last_code = 'RW'
            continue
        if item == '@roy_leaves':
            t = tl.wait(0.2)
            cut(t, 'B', zoom='kettle')
            tl.wait(1.8)
            t = tl.wait(0.0)
            cut(t, 'RW')
            key(t, 'roy', loc='walk', path=('roy_door', 'roy_gone'), u=0.0, flip=False,
                cycle=['body/walk_1', 'body/walk_2', 'body/walk_3', 'body/walk_3b', 'body/walk_4'])
            key(t + 1.0, 'roy', u=1.0, e='linear')
            key(t + 1.0, 'roy', loc='off')
            tl.sfx(t + 0.9, 'door_close', 1.0)
            tl.wait(1.5)
            continue
        if item == '@end':
            t = tl.wait(0.0)
            cut(t, 'Mc')
            key(t, 'mark', face='expressions/facepalm')
            t = tl.wait(1.9)
            cut(t, 'Gc')
            key(t, 'gary', face='expressions/sad')
            t = tl.wait(1.6)
            cut(t, '2')
            key(t, 'mark', body='upper/crossed_arms')
            key(t, 'gary', body='upper/crossed_arms')
            t = tl.wait(1.4)
            key(t, 'world', fade=0.0)
            key(t + 0.6, 'world', fade=1.0, e='ease')
            t = tl.wait(0.8)
            cut(t, 'END')
            key(t, 'world', fade=0.0)
            tl.sfx(t, 'sting', 0.8)
            tl.wait(3.5)
            continue

        # ------------------------------------------ a line of dialogue
        lid = item
        code, body, face, changes = STAGE[lid]
        who = S.SPEAKER[lid[:2]]
        gap = 0.22                        # tight: the next line comes straight in
        if lid in ('MG_03', 'GN_10', 'MG_24', 'GN_29'):
            gap = 0.5
        lead = BEAT.get(lid, 0.0)
        ln = tl.say(lid, gap=gap, lead=lead)
        perform(tl, ln)
        t0 = ln['start']
        tc = t0 - lead                    # the cut (and the pose) land before the beat
        if who == 'roy':
            key(tc, 'roy', body='body/' + body, face='expressions/' + face)
        else:
            key(tc, who, body='upper/' + body)
            if face:
                key(tc, who, face=face if '/' in face else 'expressions/' + face)
        if code != last_code or code in ('B',):
            cut(tc, code)
            last_code = code
        for word, ch in changes:
            tw = word_time(ln, word)
            if tw is None:
                continue
            if ch.startswith('body='):
                key(tw, who, body='upper/' + ch[5:])
            elif ch.startswith('face='):
                f = ch[5:]
                key(tw, who, face=f if '/' in f else 'expressions/' + f)
            elif ch == 'B':
                cut(tw, 'B')
                last_code = 'B'
                if lid == 'GN_28':
                    for j in range(3):
                        board_add(tw + 0.2 + j * 0.45, '1999_%d' % j)
                if lid == 'GN_29':
                    key(tw, 'board', zoom='1999')
            else:
                cut(tw, ch)
                last_code = ch
        if lid in BOARD_AFTER:
            t = tl.wait(0.0)
            cut(t, 'B')
            last_code = 'B'
            board_add(t + 0.2, {'MG_25': 'striker', 'RK_18': 'runs', 'MG_27': 'shirt'}[lid])
            tl.wait(BOARD_AFTER[lid])
        if lid in REACT:
            rc, rwho, rface = REACT[lid]
            t = tl.wait(0.0)
            cut(t, rc)
            last_code = rc
            if rwho:
                key(t, rwho, face='expressions/' + rface)
            tl.wait(REACT_HOLD)
    return tl


# ------------------------------------------------------------------ inserts
def board_insert(R, t, shot):
    """The whiteboard, drawn as vector art: Mark's recruitment plan so far,
    and the kettle he drew during the tea analogy."""
    import numpy as np
    sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'vec'))
    import draw as D
    import skia
    W, H = E.OUT
    surf, c = D.surface(W, H, (236, 236, 232))
    pen = D.Pen(c)
    zoom = shot.get('zoom') or R.tl.get('board', 'zoom', t)
    if zoom == 'kettle':
        pen.translate(-2350, -1100); pen.scale(1.9)
    elif zoom == '1999':
        pen.translate(-500, -1250); pen.scale(1.6)
    tf = skia.Typeface.MakeFromFile(os.path.join(HERE, '..', '..', 'fonts', 'Poppins-BoldItalic.ttf'))
    # frame and board
    pen.rect(0, 0, W, H, (40, 40, 46))
    pen.rect(90, 70, W - 90, H - 70, (244, 244, 240), r=18)
    for i in range(6):
        pen.line([(160 + i * 620, 90), (120 + i * 620, H - 90)], (232, 232, 228), 30)
    pen.rect(90, H - 110, W - 90, H - 70, (150, 150, 158))
    items = R.tl.get('board', 'items', t, ()) or ()
    blue, red, black = (30, 70, 190), (200, 30, 40), (30, 30, 36)
    if 'title' in items:
        pen.text('RECRUITMENT BOARD', 330, 330, 150, blue, font=tf, align='left')
        pen.line([(330, 380), (2180, 372)], blue, 14)
    if 'striker' in items:
        pen.text('1. STRIKER', 380, 640, 130, black, font=tf, align='left')
    if 'runs' in items:
        pen.text('(RUNS)', 1300, 640, 110, red, font=tf, align='left')
        pen.ellipse(1470, 600, 250, 95, (0, 0, 0), alpha=0, line=red, width=10)
    if 'shirt' in items:
        pen.text('2. UNDERSTANDS THE SHIRT', 380, 900, 130, black, font=tf, align='left')
    for j in range(3):
        if '1999_%d' % j in items:
            x, y, r = [(520, 1250, -6), (1150, 1400, 5), (1800, 1260, -3)][j]
            pen.save(); pen.rotate(r, x, y)
            pen.text('1999', x, y, 190, red, font=tf, align='left')
            pen.restore()
    # the kettle (drawn in the tea analogy, always there in the corner)
    k = dict(x=2900, y=1350)
    x, y = k['x'], k['y']
    body = D.smooth([(x - 230, y + 260), (x - 250, y), (x - 170, y - 180), (x, y - 220), (x + 170, y - 180), (x + 250, y), (x + 230, y + 260)])
    pen.stroke(body, black, 14)
    pen.stroke(D.smooth([(x - 170, y - 150), (x, y - 330), (x + 170, y - 150)], close=False), black, 14)
    pen.stroke(D.smooth([(x + 240, y - 40), (x + 430, y - 180), (x + 470, y - 240)], close=False), black, 14)
    pen.stroke(D.smooth([(x - 245, y - 20), (x - 330, y + 40), (x - 330, y + 160), (x - 235, y + 200)], close=False), black, 14)
    pen.text('KETTLE', x, y + 420, 110, blue, font=tf)
    pen.text('(no cup)', x, y + 540, 80, red, font=tf)
    frame = D.to_bgr(surf)
    if R.size != E.OUT:
        import cv2
        frame = cv2.resize(frame, R.size, interpolation=cv2.INTER_AREA)
    return frame


def end_card(R, t, shot):
    sys.path.insert(0, os.path.join(HERE, '..', '..', 'tools', 'vec'))
    import draw as D
    import skia
    W, H = E.OUT
    surf, c = D.surface(W, H, (14, 12, 16))
    pen = D.Pen(c)
    tf = skia.Typeface.MakeFromFile(os.path.join(HERE, '..', '..', 'fonts', 'Poppins-Bold.ttf'))
    u = t - shot['t']
    a = int(255 * min(1.0, u / 0.5))
    pen.text('EPISODE 1', W / 2, H / 2 - 200, 110, (218, 32, 44), font=tf, alpha=a)
    pen.text('INTERNATIONAL BREAK EMERGENCY', W / 2, H / 2 + 60, 190, (245, 245, 245), font=tf, alpha=a)
    pen.rect(W / 2 - 1200 * min(1, u / 0.7), H / 2 + 140, W / 2 + 1200 * min(1, u / 0.7), H / 2 + 162, (218, 32, 44), alpha=a)
    frame = D.to_bgr(surf)
    if R.size != E.OUT:
        import cv2
        frame = cv2.resize(frame, R.size, interpolation=cv2.INTER_AREA)
    return frame


E.INSERTS['board'] = board_insert
E.INSERTS['endcard'] = end_card
