"""Episode 1 - "International Break Emergency": the dialogue.

Each character's lines are numbered on their own (MG_nn Mark Goldbridge,
GN_nn Gary Neville, RK_nn Roy Keane), matching the voice files in
series/ep01/audio/<ID>.wav|.mp3. LINES holds every line's text; ORDER is the
conversation, interleaving the three lists (each keeps its own order).
Beats in ORDER that aren't line IDs are stage directions for the scene.
"""

LINES = {
    # ---------------------------------------------------------------- Mark Goldbridge
    'MG_01': "International break. Pointless. Absolutely pointless. It's like pausing your Sunday roast halfway "
             "through and somebody walking in with a Ryvita. Technically it's food, but nobody bloody asked for it.",
    'MG_02': "I woke up this morning and there wasn't even a Manchester United crisis to talk about. I checked twice.",
    'MG_03': "We're at the stage now where I've started looking at international friendlies thinking, go on then, "
             "I suppose. That's when you know things have gone seriously wrong.",
    'MG_04': "United are still United, by the way. I've taken stock. The stock's on fire.",
    'MG_05': "There is a simple answer, Gary. Do everything I've been saying for the last six years.",
    'MG_06': "New recruitment structure. Proper football people. Sporting director. Clear philosophy. "
             "Players who actually want to be there. Simple.",
    'MG_07': "They're all one answer. It's like making a cup of tea. You need water, milk, tea bag, kettle.",
    'MG_08': "That's Manchester United, Gary. We've spent two billion quid on tea and forgotten the bloody cup.",
    'MG_09': "Standards. Brilliant. Somebody ring Old Trafford. Gary's found the standards.",
    'MG_10': "Roy! Perfect timing. We're fixing Manchester United.",
    'MG_11': "Serious question. They give you control of United tomorrow. First thing you do?",
    'MG_12': "No, come on. Hypothetically. You're chief executive.",
    'MG_13': "Right, well, I've got recruitment.",
    'MG_14': "Gary can handle football operations.",
    'MG_15': "Roy handles discipline.",
    'MG_16': "And I'll do media, recruitment strategy and final say on transfers.",
    'MG_17': "Why are you looking at me like that?",
    'MG_18': "I've done about four thousand videos explaining exactly how the club should be run.",
    'MG_19': "Exactly. Experience.",
    'MG_20': "Actually, this could work.",
    'MG_21': "We build a proper structure. Gary upstairs, Roy downstairs, me overseeing football strategy.",
    'MG_22': "I'm chairman.",
    'MG_23': "Because it's my studio.",
    'MG_24': "That is literally how ownership works, Gary.",
    'MG_25': "Right. First meeting. Striker. We need one.",
    'MG_26': "No, Roy, someone who runs is not a recruitment profile.",
    'MG_27': "You know what United need? A player who understands the shirt.",
    'MG_28': "I don't know what it means either, but everyone says it and it sounds important.",
    'MG_29': "Right, international break over. We've fixed Manchester United. Someone clip this.",
    # ---------------------------------------------------------------- Gary Neville
    'GN_01': "You say that, Mark, but sometimes a break can be good. Gives everybody a chance to take stock.",
    'GN_02': "The problem at Manchester United is everybody thinks there's one simple answer.",
    'GN_03': "That's five answers already.",
    'GN_04': "You've forgotten the cup.",
    'GN_05': "You know what the problem is?",
    'GN_06': "Standards.",
    'GN_07': "Standards.",
    'GN_08': "You can laugh, but standards matter.",
    'GN_09': "Mark, you don't fix a football club with a shopping list.",
    'GN_10': "You need structure. Accountability. People who understand what Manchester United is.",
    'GN_11': "Roy, we're having a serious conversation.",
    'GN_12': "You've got to build a structure.",
    'GN_13': "I have actually been involved in running a football club.",
    'GN_14': "That was different.",
    'GN_15': "Very different circumstances.",
    'GN_16': "Mark, you have never run a football club.",
    'GN_17': "Watching one angrily on YouTube isn't experience.",
    'GN_18': "I'm not working under you.",
    'GN_19': "Why are you chairman?",
    'GN_20': "That is absolutely not how ownership works.",
    'GN_21': "If we're seriously doing this, recruitment has to be joined up.",
    'GN_22': "You can't just buy names.",
    'GN_23': "The player has to fit the culture.",
    'GN_24': "I know exactly what culture means.",
    'GN_25': "I'm just saying, when we played, there was an understanding of what the shirt meant.",
    'GN_26': "Don't start.",
    'GN_27': "Roy, that was twenty years ago.",
    'GN_28': "No, I'm not saying we sign everybody from nineteen ninety nine.",
    'GN_29': "Mark, stop writing nineteen ninety nine on the recruitment board.",
    # ---------------------------------------------------------------- Roy Keane (voice to come)
    'RK_01': "What are you two doing?",
    'RK_02': "Course you are.",
    'RK_03': "You've been talking about standards for twenty years.",
    'RK_04': "Doesn't make you interesting.",
    'RK_05': "Leave.",
    'RK_06': "Yeah. Leave.",
    'RK_07': "Seems to be what everybody else does.",
    'RK_08': "Stupid hypothetical.",
    'RK_09': "Gary, you couldn't build a shed.",
    'RK_10': "How did that go?",
    'RK_11': "You've never run one either.",
    'RK_12': "Even worse.",
    'RK_13': "No.",
    'RK_14': "No.",
    'RK_15': "Definitely no.",
    'RK_16': "You're all talking rubbish.",
    'RK_17': "You want a striker? Get someone who runs.",
    'RK_18': "Runs.",
    'RK_19': "Towards the goal preferably.",
    'RK_20': "What culture?",
    'RK_21': "Just play football.",
    'RK_22': "Footballers now need a philosophy to have breakfast.",
    'RK_23': "Back then, if you didn't run, you didn't play.",
    'RK_24': "I'm going home.",
    'RK_25': "You haven't fixed anything.",
    'RK_26': "You've drawn a kettle.",
}

# The same lines formatted for the voice generator (Clone/Clony): an emotion tag,
# pauses, ellipses, dashes, and CAPS only where the emphasis helps. The delivery
# is mostly serious - the comedy is in playing it straight. The animation reads
# the tag (face and pose) and the CAPS words (a small nod) from here.
DELIVERY = {
    'MG_01': '[frustrated] International break. Pointless. Absolutely pointless... <break time="0.5s" /> It’s like pausing your Sunday roast halfway through and somebody walking in with a Ryvita. Technically it’s food — but nobody BLOODY asked for it.',
    'MG_02': '[sigh] I woke up this morning and there wasn’t even a Manchester United crisis to talk about. <break time="0.5s" /> I checked twice.',
    'MG_03': '[frustrated] We’re at the stage now where I’ve started looking at international friendlies thinking... “Go on then, I suppose.” <break time="0.5s" /> That’s when you know things have gone seriously wrong.',
    'MG_04': '[dry] United are still United, by the way. I’ve taken stock. <break time="0.5s" /> The stock’s on fire.',
    'MG_05': '[confident] There IS a simple answer, Gary. <break time="0.5s" /> Do everything I’ve been saying for the last six years.',
    'MG_06': '[matter-of-fact] New recruitment structure. Proper football people. Sporting director. Clear philosophy. Players who actually want to be there. <break time="0.5s" /> Simple.',
    'MG_07': '[explaining] They’re all one answer. It’s like making a cup of tea. You need water, milk, tea bag, kettle—',
    'MG_08': '[deadpan] That’s Manchester United, Gary. <break time="0.5s" /> We’ve spent two billion quid on tea... and forgotten the bloody cup.',
    'MG_09': '[sarcastic] Standards. Brilliant. <break time="0.5s" /> Somebody ring Old Trafford. Gary’s found the STANDARDS.',
    'MG_10': '[energised] Roy! Perfect timing. We’re fixing Manchester United.',
    'MG_11': '[curious] Serious question. They give you control of United tomorrow... first thing you do?',
    'MG_12': '[insistent] No, come on. Hypothetically. You’re chief executive.',
    'MG_13': '[confident] Right, well... I’ve got recruitment.',
    'MG_14': '[matter-of-fact] Gary can handle football operations.',
    'MG_15': '[matter-of-fact] Roy handles discipline.',
    'MG_16': '[confident] And I’ll do media, recruitment strategy... and final say on transfers.',
    'MG_17': '[confused] Why are you looking at me like that?',
    'MG_18': '[defensive] I’ve done about FOUR THOUSAND videos explaining exactly how the club should be run.',
    'MG_19': '[smug] Exactly. <break time="0.5s" /> Experience.',
    'MG_20': '[realising] Actually... this could work.',
    'MG_21': '[building excitement] We build a proper structure. Gary upstairs, Roy downstairs... me overseeing football strategy.',
    'MG_22': '[matter-of-fact] I’m chairman.',
    'MG_23': '[deadpan] Because it’s my studio.',
    'MG_24': '[confident] That is literally how ownership works, Gary.',
    'MG_25': '[businesslike] Right. First meeting. <break time="0.5s" /> Striker. We need one.',
    'MG_26': '[frustrated] No, Roy... “someone who runs” is NOT a recruitment profile.',
    'MG_27': '[earnest] You know what United need? <break time="0.5s" /> A player who understands the shirt.',
    'MG_28': '[dry] I don’t know what it means either... but everyone says it and it sounds important.',
    'MG_29': '[satisfied] Right, international break over. We’ve fixed Manchester United. <break time="0.5s" /> Someone clip this.',
    'GN_01': '[calm] You say that, Mark, but sometimes a break can be good. <break time="0.5s" /> Gives everybody a chance to take stock.',
    'GN_02': '[serious] The problem at Manchester United is everybody thinks there’s one simple answer.',
    'GN_03': '[dry] That’s five answers already.',
    'GN_04': '[deadpan] You’ve forgotten the cup.',
    'GN_05': '[serious] You know what the problem is?',
    'GN_06': '[firm] Standards.',
    'GN_07': '[firmer] STANDARDS.',
    'GN_08': '[serious] You can laugh, but standards matter.',
    'GN_09': '[measured] Mark, you don’t fix a football club with a shopping list.',
    'GN_10': '[earnest] You need structure. Accountability. People who understand what Manchester United IS.',
    'GN_11': '[mildly annoyed] Roy, we’re having a serious conversation.',
    'GN_12': '[insistent] You’ve got to build a structure.',
    'GN_13': '[defensive] I HAVE actually been involved in running a football club.',
    'GN_14': '[awkward] That was different.',
    'GN_15': '[more defensive] Very different circumstances.',
    'GN_16': '[matter-of-fact] Mark, you have never run a football club.',
    'GN_17': '[dry] Watching one angrily on YouTube isn’t experience.',
    'GN_18': '[firm] I’m not working under you.',
    'GN_19': '[confused] Why are YOU chairman?',
    'GN_20': '[exasperated] That is absolutely NOT how ownership works.',
    'GN_21': '[serious] If we’re seriously doing this, recruitment has to be joined up.',
    'GN_22': '[measured] You can’t just buy names.',
    'GN_23': '[earnest] The player has to fit the culture.',
    'GN_24': '[defensive] I know exactly what culture means.',
    'GN_25': '[nostalgic] I’m just saying... when we played, there was an understanding of what the shirt meant.',
    'GN_26': '[warning] Don’t start.',
    'GN_27': '[annoyed] Roy, that was twenty years ago.',
    'GN_28': '[exasperated] No, I’m NOT saying we sign everybody from 1999.',
    'GN_29': '[frustrated] Mark... stop writing “1999” on the recruitment board.',
    'RK_01': '[deadpan] What are you two doing?',
    'RK_02': '[dry] Course you are.',
    'RK_03': '[flat] You’ve been talking about standards for twenty years.',
    'RK_04': '[deadpan] Doesn’t make you interesting.',
    'RK_05': '[matter-of-fact] Leave.',
    'RK_06': '[firm] Yeah. Leave.',
    'RK_07': '[dry] Seems to be what everybody else does.',
    'RK_08': '[dismissive] Stupid hypothetical.',
    'RK_09': '[deadpan] Gary... you couldn’t build a shed.',
    'RK_10': '[dry] How did that go?',
    'RK_11': '[matter-of-fact] You’ve never run one either.',
    'RK_12': '[flat] Even worse.',
    'RK_13': '[firm] No.',
    'RK_14': '[firmer] No.',
    'RK_15': '[very firm] Definitely no.',
    'RK_16': '[annoyed] You’re all talking rubbish.',
    'RK_17': '[matter-of-fact] You want a striker? Get someone who runs.',
    'RK_18': '[flat] Runs.',
    'RK_19': '[dry] Towards the goal preferably.',
    'RK_20': '[confused] What culture?',
    'RK_21': '[deadpan] Just play football.',
    'RK_22': '[dry] Footballers now need a philosophy to have breakfast.',
    'RK_23': '[firm] Back then, if you didn’t run... you didn’t play.',
    'RK_24': '[finished] I’m going home.',
    'RK_25': '[deadpan] You haven’t fixed anything.',
    'RK_26': '[dry] You’ve drawn a kettle.',
}


def tag(lid):
    """The delivery's emotion tag, e.g. 'frustrated'."""
    t = DELIVERY.get(lid, '')
    return t[1:t.index(']')] if t.startswith('[') else ''


def emphasised(lid):
    """Words written in CAPS for emphasis (lower-cased, as in the alignment)."""
    import re
    body = re.sub(r'^\[[^\]]*\]|<[^>]*>', ' ', DELIVERY.get(lid, ''))
    return [w.lower() for w in re.findall(r"[A-Za-z’']+", body) if len(w) > 1 and w.isupper()]


SPEAKER = {'MG': 'mark', 'GN': 'gary', 'RK': 'roy'}

# The conversation, in order. Every character's own lines stay in their order.
ORDER = [
    # 1. Mark alone at his desk
    'MG_01', 'MG_02', 'MG_03',
    '@gary_enters',
    'GN_01', 'MG_04', 'GN_02', 'MG_05', 'MG_06', 'GN_03', 'MG_07', 'GN_04', 'MG_08',
    'GN_05', 'GN_06', 'MG_09', 'GN_07', 'GN_08', 'GN_09', 'GN_10',
    '@roy_enters',
    'RK_01', 'MG_10', 'RK_02', 'RK_03', 'RK_04', 'GN_11',
    'MG_11', 'RK_05', 'MG_12', 'RK_06', 'RK_07', 'RK_08',
    'GN_12', 'RK_09', 'GN_13', 'RK_10', 'GN_14', 'GN_15',
    'MG_13', 'MG_14', 'MG_15', 'MG_16', 'MG_17',
    'GN_16', 'RK_11', 'MG_18', 'GN_17', 'MG_19', 'RK_12',
    'MG_20', 'RK_13', 'MG_21', 'RK_14', 'GN_18', 'MG_22', 'RK_15', 'GN_19', 'MG_23', 'GN_20', 'MG_24',
    'RK_16',
    '@board',
    'GN_21', 'MG_25', 'RK_17', 'MG_26', 'RK_18', 'RK_19', 'GN_22', 'GN_23', 'RK_20', 'RK_21', 'GN_24',
    'MG_27', 'MG_28', 'GN_25', 'RK_22', 'GN_26', 'RK_23', 'GN_27', 'GN_28', 'GN_29',
    'RK_24', '@roy_heads_out',
    'MG_29', 'RK_25', 'RK_26',
    '@roy_leaves',
    '@end',
]


def check():
    ids = [x for x in ORDER if not x.startswith('@')]
    assert sorted(ids) == sorted(LINES), set(LINES) ^ set(ids)
    assert sorted(DELIVERY) == sorted(LINES), set(LINES) ^ set(DELIVERY)
    for p in SPEAKER:
        mine = [x for x in ids if x.startswith(p)]
        assert mine == sorted(mine), (p, mine)


check()
