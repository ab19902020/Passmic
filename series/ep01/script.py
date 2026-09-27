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
    'MG_29',
    '@roy_leaves',
    'RK_24', 'RK_25', 'RK_26',
    '@end',
]


def check():
    ids = [x for x in ORDER if not x.startswith('@')]
    assert sorted(ids) == sorted(LINES), set(LINES) ^ set(ids)
    for p in SPEAKER:
        mine = [x for x in ids if x.startswith(p)]
        assert mine == sorted(mine), (p, mine)


check()
