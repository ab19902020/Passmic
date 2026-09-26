"""INT. CARTMAN'S BEDROOM - DAY   (South Manchester, cold open)

Built as a vector scene: python3 tools/render_episode.py episode/scenes/cartman_room.py [4k|1080p|still t ...]

Voice clips (episode/audio/clipNN.mp3, clip_monaco.mp3) are in script order;
the Monaco clip plays between clip 4 and clip 5.
"""
import os
from engine import Timeline
import room as R
from cartman import REST

EP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CLIP = lambda n: os.path.join(EP, 'audio', 'clip%02d.mp3' % n)
CLIP_MONACO = os.path.join(EP, 'audio', 'clip_monaco.mp3')

# What is said in each clip, for word-driven lip sync. <unk:N> / <laugh:N> mark
# N syllables of sound in the clip that aren't in the script.
TEXT = {
    1: "You know... I never thought I'd say this, but I fucking love Manchester United. Like, seriously. "
       "I started watching because I thought their little red devil guy was pretty badass. "
       "But then I learned about everything.",
    2: "Cantona. Rooney. Ronaldo. Beckham. Keane. The Class of '92. That Champions League final where they "
       "scored twice at the end and the Germans looked all sad and shit. It was awesome. "
       "And then there's Sir Alex Ferguson.",
    3: "That dude understood something. You don't ask people nicely to be good at football. You scream at them "
       "until they're terrified of disappointing you. That's leadership. But then I started learning about the owners.",
    4: "The fucking Glazers. These guys bought Manchester United, loaded debt onto it, and United fans have been "
       "pissed off with them for years. And then there's Jim Ratcliffe. <unk:5>",
    'monaco': "This motherfucker owns part of Manchester United while living in Monaco. Monaco! You can't be sitting "
              "on a yacht in Monaco making decisions about Manchester United! Well... actually, that sounds pretty sweet.",
    5: "No! That's not the point! Manchester United belongs to the fans. The people freezing their asses off outside "
       "Old Trafford. The people spending all their money on shirts. The people whose entire fucking weekend gets "
       "ruined because eleven millionaires couldn't defend a corner!",
    6: "Those people deserve better! And that's when I realised something... Maybe Manchester United doesn't need "
       "another billionaire. Maybe Manchester United needs someone who actually understands the fans.",
    7: "Someone strong. Someone brave. Someone who's willing to make the difficult decisions. Someone like... "
       "Eric fucking Cartman.",
    8: "Yeah. I'm gonna save Manchester United. And those assholes are gonna fucking love me for it. <laugh:10>",
}

K = 3.4                                       # Cartman units -> world px near the camera
CX, SY = R.CHAIR_X, R.SEAT_Y
SIT_SIDE = dict(x=CX - 30, y=R.SEAT_TOP + 6)         # seated, facing the monitor (right)
SIT_FRONT = dict(x=CX, y=R.SEAT_TOP + 18)             # seated, turned to camera
STAND_SEAT = dict(x=CX, y=R.SEAT_TOP + 6)             # standing on the seat
DESK_SHOT = (1700, 580, 1850)                 # camera rects (x0, y0, width) in world px
DESK_TIGHT = (1820, 590, 1620)
CHAIR_WIDE = (1380, 640, 1580)

DOC = ['OPERATION: SAVE MANCHESTER UNITED', 'OBJECTIVE 1: GET RID OF THE GLAZERS',
       'OBJECTIVE 2: GET RID OF JIM RATCLIFFE', 'OBJECTIVE 3: CARTMAN TAKES CONTROL']
DOC_N = [len(s) for s in DOC]


def sc(y):
    """Perspective: smaller further back (towards the wall at y=1320)."""
    return K * (0.64 + 0.36 * (y - 1320) / 480.0)


def turn_to_screen(tl, t, **kw):
    tl.key(t, e='step', view='right', body='sit', lean=0.0, arm_r=35.0, hand_r='mitten', look=(1.0, -0.25), **SIT_SIDE, **kw)
    tl.set(t, e='step', chair_view='side')


def turn_to_camera(tl, t, **kw):
    tl.key(t, e='step', view='front', body='sit', lean=0.0, look=(0.0, 0.0), arm_l=REST, arm_r=REST,
           hand_l='mitten', hand_r='mitten', arms_front=False, **SIT_FRONT, **kw)
    tl.set(t, e='step', chair_view='front')


def build():
    tl = Timeline(fps=24)
    k, st = tl.key, tl.set

    # ------------------------------------------------ cold open: nobody, door shut
    st(0, e='step', door=0.0, screen='match', screen_p=dict(score='UNITED  3 - 0', clock="64'"), chair_view='side', fade=1.0)
    st(0.7, fade=0.0)
    k(0, e='step', visible=False, view='front', body='walk', x=385.0, y=1330.0, s=sc(1330), mouth='rest',
      brows='none', lid_top=0.0, lid_bot=0.0, look=(0.0, 0.0), squash=0.0, lean=0.0, jitter=0.0, nod=0.0,
      shakehead=0.0, head_dx=0.0, head_dy=0.0, head_tilt=0.0, arm_l=REST, arm_r=REST, pupil=1.0, brow_amt=1.0,
      bend_l=0.0, bend_r=0.0, hand_abs_l=None, hand_abs_r=None, hand_rot_l=0.0, hand_rot_r=0.0,
      stride=150.0, talk=True, loud_mouth=None, tilt_talk=1.0)
    tl.shot(0, 'wide')
    tl.wait(1.1)

    # the door opens, Cartman steps in, turns round and shuts it behind him
    DOOR_X = 385.0
    t = tl.wait(0.8)
    st(t, door=0.0); st(t + 0.7, door=1.0, e='out')
    tl.sfx(t, 'door_open', 1.0)
    t = tl.wait(0.9)
    k(t, e='step', visible=True, view='front', body='walk')
    k(t, x=DOOR_X, y=1335.0, s=sc(1335)); k(t + 0.8, e='linear', x=DOOR_X, y=1420.0, s=sc(1420))
    t = tl.wait(0.9)
    k(t, e='step', view='back', body='stand', arm_l=REST)
    k(t + 0.2, arm_l=100.0, e='out'); k(t + 0.85, arm_l=REST)
    st(t + 0.25, door=1.0); st(t + 0.7, door=0.0, e='in')
    tl.sfx(t + 0.55, 'door_close', 1.0)
    t = tl.wait(1.1)
    # walks down into the room, clear of the bed...
    k(t, e='step', view='front', body='walk')
    k(t, x=DOOR_X, y=1420.0, s=sc(1420)); k(t + 1.6, e='linear', x=DOOR_X + 20, y=1740.0, s=sc(1740))
    t = tl.wait(1.6)

    # ...and crosses the room to his computer without a word
    t = tl.wait(3.6)
    k(t, e='step', view='right', body='walk', arm_r=12.0)
    k(t, x=DOOR_X + 20, y=1740.0, s=sc(1740)); k(t + 3.5, e='linear', x=CX - 330, y=1800.0, s=sc(1800))
    tl.shot(t + 1.6, 'rect', rect=(900, 420, 3000))

    # climbs onto the computer chair and shuffles comfortable
    t = tl.wait(0.5)
    k(t, e='step', body='stand')
    t = tl.wait(0.55)
    k(t, squash=0.0); k(t + 0.12, squash=0.18, e='out'); k(t + 0.2, squash=-0.1)
    k(t + 0.2, x=CX - 160, y=SY - 60, e='out'); k(t + 0.45, e='in', **SIT_SIDE)
    k(t + 0.45, e='step', body='sit', s=K); k(t + 0.45, squash=0.22); k(t + 0.6, squash=0.0, e='out')
    tl.sfx(t + 0.1, 'hop', 1.0); tl.sfx(t + 0.42, 'cushion', 1.0)
    t = tl.wait(1.1)
    k(t, jitter=5.0); k(t + 0.9, jitter=0.0)
    tl.sfx(t + 0.1, 'chair_creak', 0.8)
    k(t, head_tilt=4.0); k(t + 0.4, head_tilt=-4.0); k(t + 0.8, head_tilt=0.0)
    tl.shot(t, 'rect', rect=DESK_SHOT)

    # looks up at the screen: a United video is playing
    t = tl.wait(1.0)
    k(t, look=(1.0, -0.35))
    t = tl.wait(3.0)
    tl.shot(t, 'screen')
    st(t, e='step', screen='match', screen_p=dict(caption='MANCHESTER UNITED  -  GREATEST GOALS', score='UNITED  3 - 0', clock="67'"))
    t = tl.wait(1.6)
    tl.shot(t, 'rect', rect=DESK_SHOT)
    k(t + 0.6, look=(1.0, -0.2))

    # ------------------------------------------------ "You know... I fucking love Manchester United."
    f = tl.say(CLIP(1), text=TEXT[1])
    k(f(0), mouth='smile', e='step')
    tl.shot(f(0), 'rect', rect=DESK_SHOT)
    # "Like, seriously." He leans toward the screen.
    k(f(4.6), lean=0.0); k(f(5.1), lean=9.0, e='out')
    tl.shot(f(4.62), 'rect', rect=DESK_TIGHT)
    # "...their little red devil guy was pretty badass."
    tl.shot(f(6.6), 'screen')
    st(f(6.6), e='step', screen='devil', screen_p={})
    # "But then I learned about everything."
    turn_to_camera(tl, f(9.25), mouth='smirk', brows='none')
    st(f(9.25), e='step', screen='match', screen_p={})
    tl.shot(f(9.25), 'medium', w=1500)

    # ------------------------------------------------ counting on his fingers
    f = tl.say(CLIP(2), text=TEXT[2])
    names = [0.05, 0.9, 1.6, 2.65, 3.5]
    COUNT = dict(arms_front=True, arm_r=40.0, bend_r=120.0, hand_abs_r=180.0, arm_l=40.0, bend_l=110.0, hand_abs_l=-80.0)
    k(f(0), e='step', hand_l='point', **{kk: v for kk, v in COUNT.items() if not isinstance(v, float)})
    k(f(0), e='step', bend_r=120.0, bend_l=110.0, hand_abs_r=180.0, hand_abs_l=-80.0)
    k(f(0), arm_r=REST, arm_l=REST); k(f(0.25), arm_r=40.0, arm_l=40.0, e='back')
    for i, tn in enumerate(names):
        k(f(tn), e='step', hand_r='count%d' % (i + 1))
        k(f(tn), e='step', head_tilt=0.0); k(f(tn) + 0.1, head_tilt=(-3.0 if i % 2 else 3.0), e='out')
    # "The Class of '92": both hands out
    k(f(4.3), e='step', hand_r='open', hand_l='open', bend_r=0.0, bend_l=0.0, hand_abs_r=None, hand_abs_l=None)
    k(f(4.3), arm_r=REST, arm_l=REST); k(f(4.6), arm_r=100.0, arm_l=100.0, e='back'); k(f(5.6), arm_r=REST, arm_l=REST)
    k(f(5.6), e='step', hand_r='mitten', hand_l='mitten', arms_front=False)
    # "That Champions League final where they scored twice at the end..."
    tl.shot(f(6.2), 'screen')
    st(f(6.2), e='step', screen='match', screen_p=dict(score='MAN UTD  2 - 1  BAYERN', clock="90+3'", caption='1999  -  THEY SCORED TWICE AT THE END', roar=1.0))
    tl.cheer(f(6.4))
    # "...and the Germans looked all sad and shit." Cartman smiles.
    tl.shot(f(9.7), 'medium', w=1500)
    k(f(9.7), e='step', mouth='smirk', arms_front=False)
    # "It was awesome."
    tl.shot(f(11.6), 'close', w=950)
    k(f(11.6), e='step', mouth='grin', lid_bot=0.2)
    # "And then there's Sir Alex Ferguson."  - unusually sincere
    tl.shot(f(13.45), 'close', w=1000)
    k(f(13.45), e='step', mouth='rest', lid_bot=0.0, brows='worried', brow_amt=0.6, pupil=1.25, look=(0.0, -0.1))
    st(f(13.45), e='step', screen='manager', screen_p=dict(caption='SIR ALEX FERGUSON'))

    # ------------------------------------------------ Sir Alex
    f = tl.say(CLIP(3), text=TEXT[3])
    k(f(0), e='step', mouth='rest')
    # "You don't ask people nicely..." - points toward the computer
    tl.shot(f(1.75), 'medium', w=1600)
    k(f(1.75), e='step', brows='determined', brow_amt=0.8, pupil=1.0, arms_front=False)
    k(f(1.75), arm_r=REST, hand_r='mitten'); k(f(2.1), arm_r=92.0, e='back')
    k(f(2.1), e='step', hand_r='point', look=(0.6, 0.0))
    tl.shot(f(4.65), 'screen')
    st(f(4.65), e='step', screen='manager', screen_p=dict(caption='SIR ALEX FERGUSON'))
    tl.shot(f(6.9), 'medium', w=1500)
    k(f(6.9), e='step', brows='angry', brow_amt=1.0, arm_r=140.0, hand_r='fist', arm_l=REST, look=(0.0, 0.0), loud_mouth='shout')
    # "That's leadership."  - nods approvingly
    tl.shot(f(8.1), 'close', w=950)
    k(f(8.1), e='step', brows='determined', brow_amt=0.6, arm_r=REST, hand_r='mitten', mouth='smirk', nod=1.0, loud_mouth=None)
    k(f(9.3), e='step', nod=0.0)
    # "But then I started learning about the owners."
    turn_to_screen(tl, f(9.45), brows='none', mouth='rest')
    st(f(9.45), e='step', screen='news', screen_p=dict(headline='WHO OWNS MANCHESTER UNITED?', kind='chart', grow=0.0))
    tl.shot(f(9.45), 'rect', rect=DESK_SHOT)

    # ------------------------------------------------ the owners
    f = tl.say(CLIP(4), text=TEXT[4])
    # "The fucking Glazers." - his expression changes
    tl.shot(f(0), 'close', w=1000)
    k(f(0), e='step', brows='angry', mouth='frown', loud_mouth='shout')
    # "These guys bought Manchester United, loaded debt onto it..."
    tl.shot(f(1.85), 'screen')
    st(f(1.85), e='step', screen='news', screen_p=dict(headline='THE GLAZER TAKEOVER', kind='chart', grow=0.0))
    for i in range(1, 13):
        st(f(1.85 + i * 0.27), e='step', screen_p=dict(headline='THE GLAZER TAKEOVER', kind='chart', grow=i / 12))
    tl.shot(f(5.4), 'medium', w=1500)
    turn_to_camera(tl, f(5.4), brows='angry', mouth='frown')
    k(f(5.4), e='step', arm_l=100.0, arm_r=100.0, hand_l='open', hand_r='open')
    # "And THEN there's Jim Ratcliffe."  - clicks his mouse
    turn_to_screen(tl, f(8.6), brows='angry', mouth='frown')
    tl.shot(f(8.6), 'rect', rect=DESK_TIGHT)
    k(f(8.6), arm_r=35.0); k(f(8.8), arm_r=75.0, e='out')
    tl.sfx(f(8.85), 'click', 1.0)
    st(f(8.85), e='step', screen='news', screen_p=dict(headline='NEW PART-OWNER', kind='profile', name='JIM RATCLIFFE',
                                                        facts=['Owns part of United', 'Lives in Monaco']))
    tl.shot(f(9.7), 'screen')

    # ------------------------------------------------ Monaco
    # Another click. "This motherfucker owns part of Manchester United while living in Monaco."
    f = tl.say(CLIP_MONACO, text=TEXT['monaco'])
    t = f(0) - 0.55
    tl.shot(t, 'rect', rect=DESK_TIGHT)
    k(t, arm_r=35.0); k(t + 0.15, arm_r=75.0, e='out'); k(t + 0.4, arm_r=35.0)
    tl.sfx(t + 0.2, 'click', 1.0)
    st(t + 0.2, e='step', screen='monaco', screen_p=dict(caption='JIM RATCLIFFE - MONACO'))
    k(t, e='step', brows='angry', brow_amt=0.8, mouth='frown', look=(1.0, -0.2), loud_mouth=None)
    tl.shot(f(1.3), 'close', w=1000)
    # "...while living in Monaco."  - the yacht on screen
    tl.shot(f(2.85), 'screen')
    # he stares incredulously at the screen: "Monaco!"
    tl.shot(f(4.75), 'close', w=900)
    k(f(4.75), e='step', brows='raised', brow_amt=1.0, pupil=0.7, mouth='o', look=(1.0, -0.2))
    k(f(5.05), e='step', loud_mouth='shout')
    k(f(5.0), squash=0.0); k(f(5.1), squash=-0.12, e='out'); k(f(5.35), squash=0.0)
    # he throws both hands outward: "You can't be sitting on a yacht in Monaco making decisions about Manchester United!"
    turn_to_camera(tl, f(6.2), brows='angry', brow_amt=1.0, mouth='frown', pupil=1.0, loud_mouth='shout')
    tl.shot(f(6.2), 'medium', w=1600)
    k(f(6.2), e='step', hand_l='open', hand_r='open')
    k(f(6.2), arm_l=REST, arm_r=REST); k(f(6.45), arm_l=102.0, arm_r=102.0, e='back')
    k(f(8.3), arm_l=102.0, arm_r=102.0); k(f(8.45), arm_l=118.0, arm_r=118.0, e='back'); k(f(8.7), arm_l=102.0, arm_r=102.0)
    # beat. Cartman thinks about that.
    tl.shot(f(10.4), 'close', w=950)
    k(f(10.4), arm_l=102.0, arm_r=102.0); k(f(10.9), arm_l=REST, arm_r=REST)
    k(f(10.4), e='step', hand_l='mitten', hand_r='mitten', brows='none', loud_mouth=None, mouth='rest', look=(0.35, -0.8))
    # "Well... actually, that sounds pretty sweet."  - a dreamy aside
    k(f(11.9), e='step', lid_top=0.3, mouth='smile', look=(0.4, -0.85))
    k(f(11.9), head_tilt=0.0); k(f(12.8), head_tilt=6.0)
    k(f(13.95), e='step', lid_top=0.0, look=(0.0, 0.0), head_tilt=0.0)

    # ------------------------------------------------ "No! That's not the point!" - then increasingly worked up
    f = tl.say(CLIP(5), text=TEXT[5])
    k(f(0), e='step', brows='angry', brow_amt=1.0, mouth='frown', loud_mouth='shout')
    k(f(0.05), shakehead=0.0); k(f(0.15), shakehead=1.0, e='out'); k(f(0.75), shakehead=0.0)
    tl.shot(f(2.05), 'medium', w=1600)
    beats = [(2.05, 102, 102, 'open', 'open'),     # "Manchester United belongs to the fans."
             (4.95, 140, REST, 'fist', 'mitten'),  # "The people freezing their asses off outside Old Trafford."
             (7.8, REST, 92, 'mitten', 'point'),   # "The people spending all their money on shirts."
             (10.1, 135, 135, 'open', 'open'),     # "The people whose entire fucking weekend gets ruined"
             (12.1, 112, 112, 'fist', 'fist')]     # "because eleven millionaires couldn't defend a corner!"
    for tb, al, ar, hl, hr in beats:
        k(f(tb), e='step', hand_l=hl, hand_r=hr)
        k(f(tb) + 0.18, arm_l=float(al), arm_r=float(ar), e='back')
    tl.shot(f(12.1), 'close', w=1000)

    # he stands on the chair: "Those people deserve better!"
    t = tl.wait(0.25)
    tl.shot(t, 'rect', rect=CHAIR_WIDE)
    k(t, squash=0.15, e='out'); k(t + 0.15, e='step', body='stand', **STAND_SEAT); k(t + 0.15, squash=-0.08); k(t + 0.3, squash=0.0)
    k(t + 0.15, arm_l=140.0, arm_r=140.0, hand_l='fist', hand_r='fist', e='back')
    tl.sfx(t + 0.05, 'chair_creak', 1.0)
    f = tl.say(CLIP(6), 0.0, 1.95, gap=0.0, text=TEXT[6])
    k(f(0), e='step', brows='angry', brow_amt=1.2, loud_mouth='shout')

    # pause - a thought occurs to him, the anger drains away, he sits back down
    t = tl.wait(3.2)
    k(t + 0.4, arm_l=140.0, arm_r=140.0); k(t + 1.2, arm_l=REST, arm_r=REST, e='inout')
    k(t + 0.6, e='step', brows='none', loud_mouth=None, mouth='rest', look=(0.3, -0.7), lid_top=0.15)
    k(t + 0.6, e='step', hand_l='mitten', hand_r='mitten')
    k(t + 1.6, **STAND_SEAT); k(t + 2.8, e='inout', **SIT_FRONT)
    k(t + 2.2, e='step', body='sit')
    k(t + 2.8, look=(0.0, 0.0), lid_top=0.0)
    tl.shot(t + 1.4, 'medium', w=1700)

    # ------------------------------------------------ mock-inspirational
    f = tl.say(CLIP(6), 2.0, None, gap=0.9, text=TEXT[6])
    tl.shot(f(2.0), 'close', w=1050)
    k(f(2.0), e='step', brows='worried', brow_amt=0.7, lid_top=0.12, look=(0.0, -0.25), pupil=1.15)
    # "Maybe Manchester United doesn't need another billionaire." - looks directly ahead
    k(f(4.3), look=(0.0, 0.0))
    tl.shot(f(7.7), 'close', w=900)
    # another pause... a tiny smile appears
    k(f(11.9) + 0.3, e='step', mouth='smirk')
    f = tl.say(CLIP(7), 0.0, 6.9, gap=0.55, text=TEXT[7])
    tl.shot(f(0), 'close', w=880)
    k(f(0), e='step', brows='determined', brow_amt=0.8, pupil=1.0, mouth='smirk', lid_top=0.0)
    k(f(5.8), lid_top=0.22)
    # "Eric fucking Cartman." - both thumbs at himself
    f = tl.say(CLIP(7), 6.95, None, gap=1.7, text=TEXT[7])
    tl.shot(f(6.95), 'medium', w=1450)
    k(f(6.95), e='step', lid_top=0.0, mouth='grin', brows='determined', brow_amt=0.8, arms_front=True,
      hand_l='thumb', hand_r='thumb', hand_rot_l=-90.0, hand_rot_r=-90.0, bend_l=140.0, bend_r=140.0)
    k(f(6.95), arm_l=REST, arm_r=REST); k(f(7.2), arm_l=50.0, arm_r=50.0, e='back')

    # ------------------------------------------------ OPERATION: SAVE MANCHESTER UNITED
    t = tl.wait(1.1)
    turn_to_screen(tl, t, brows='none', mouth='rest', bend_l=0.0, bend_r=0.0, hand_rot_l=0.0, hand_rot_r=0.0,
                   arms_front=False)
    tl.shot(t, 'rect', rect=DESK_TIGHT)
    k(t, arm_r=35.0); k(t + 0.3, arm_r=75.0, e='out')
    tl.sfx(t + 0.5, 'click', 1.0)
    st(t, e='step', screen='desktop', screen_p={})
    st(t + 0.55, e='step', screen='document', screen_p=dict(lines=DOC, chars=0))

    def type_line(t0, upto, dur):
        start = sum(DOC_N[:upto - 1])
        n = DOC_N[upto - 1]
        for i in range(n + 1):
            st(t0 + dur * i / n, e='step', screen_p=dict(lines=DOC, chars=start + i))
        tl.sfx(t0, 'typing', 1.0, dur=dur, rate=len(DOC[upto - 1]) / dur, seed=upto)

    t = tl.wait(6.2)                       # the document fills up
    tl.shot(t, 'screen')
    type_line(t + 0.3, 1, 2.6)
    type_line(t + 3.3, 2, 2.7)
    t = tl.wait(1.3)                       # Cartman hammering the keyboard
    tl.shot(t, 'rect', rect=DESK_TIGHT)
    for i in range(14):                    # hammering the keys
        k(t + i * 0.11, e='step', arm_r=(84.0 if i % 2 else 74.0), head_dy=(1.5 if i % 2 else 0.0))
    k(t + 1.6, e='step', arm_r=35.0, head_dy=0.0)
    tl.sfx(t, 'typing', 1.2, dur=1.5, rate=13, seed=9)
    t = tl.wait(3.2)
    tl.shot(t, 'screen')
    type_line(t + 0.2, 3, 2.8)
    t = tl.wait(1.9)                       # Cartman thinks...
    tl.shot(t, 'close', w=1000)
    k(t, e='step', arm_r=35.0, look=(0.3, -0.9), brows='worried', brow_amt=0.5, mouth='rest')
    k(t + 1.3, look=(1.0, -0.2))
    t = tl.wait(3.3)                       # ...then types
    tl.shot(t, 'screen')
    type_line(t + 0.3, 4, 2.6)
    t = tl.wait(1.1)                       # he smiles
    tl.shot(t, 'close', w=1000)
    k(t, e='step', mouth='grin', brows='none', lid_top=0.22, look=(1.0, -0.2))

    # ------------------------------------------------ "Yeah. I'm gonna save Manchester United."
    f = tl.say(CLIP(8), 0.0, None, gap=0.3, text=TEXT[8])
    turn_to_camera(tl, f(0.1), mouth='smirk', brows='none', lid_top=0.25)
    tl.shot(f(0.1), 'close', w=900)
    turn_to_screen(tl, f(1.2), mouth='smirk', brows='none', lid_top=0.25)
    tl.shot(f(1.2), 'rect', rect=DESK_SHOT)
    # "And those assholes are gonna fucking love me for it."
    tl.shot(f(3.7), 'close', w=1000)
    k(f(6.3), e='step', mouth='laugh', lid_top=0.3, nod=0.8)

    # ------------------------------------------------ title
    t = tl.wait(4.0)
    tl.shot(t, 'title', text='SOUTH MANCHESTER')
    tl.sting(t)
    st(t + 3.2, fade=0.0); st(t + 4.0, fade=1.0)
    return tl
