"""
NameContextClassifier
---------------------
Classifies a full name into:
  - cultural_origin : SL_SINHALA | SL_TAMIL | SL_MUSLIM | INTL
  - gender          : male | female | unknown
  - confidence      : 0.0 – 1.0

Strategy (no SLM required):
  1. Surname lookup → strongest signal for cultural_origin
  2. Suffix pattern matching → secondary signal for SL origins
  3. First-name lookup → gender detection per cultural origin
  4. Fallback suffix heuristic for gender when name not in lists
"""


class NameContextClassifier:

    # ------------------------------------------------------------------
    # Surname dictionaries
    # ------------------------------------------------------------------

    _SL_SINHALA_SURNAMES = {
        'perera', 'fernando', 'silva', 'jayasuriya', 'rajapaksa', 'gunawardena',
        'dissanayake', 'senanayake', 'wickramasinghe', 'bandara', 'kotelawala',
        'jayewardene', 'kumaratunga', 'wijesekera', 'rathnayake', 'pathirana',
        'weerasinghe', 'karunaratne', 'liyanage', 'amarasinghe', 'jayasena',
        'gunasekara', 'dasanayake', 'herath', 'wijeratne', 'siriwardena',
        'samaraweera', 'thilakarathna', 'ranaweera', 'alwis', 'gamage',
        'abeysekera', 'ratnayake', 'lokuge', 'fonseka', 'jayantha',
        'wimalasiri', 'dassanayake', 'premadasa', 'jayakody', 'edirisinghe',
        'de silva', 'de mel', 'de zoysa', 'de alwis', 'de saram',
        'wijesuriya', 'rajapakshe', 'wickremasinghe', 'senanayaka', 'abeywickrama',
        'koswatte', 'nugawela', 'karunanayake', 'attanayake', 'nanayakkara',
        'jayawardena', 'jayaratne', 'rajakaruna', 'rajapakshe', 'madurawala',
        'kahawatte', 'hapugoda', 'ranatunga', 'mendis', 'pieris', 'dias',
        'jayalath', 'samarakoon', 'wickramaratne', 'hettiarachchi', 'goonewardena',
        'wijewardena', 'rajasingham', 'daluwatte', 'peirs', 'peiris',
    }

    _SL_TAMIL_SURNAMES = {
        'rajasingam', 'balakrishnan', 'subramaniam', 'thambipillai', 'krishnaswamy',
        'selvam', 'ratnasabapathy', 'kanthasamy', 'arumugam', 'chelvanayagam',
        'jeyaratnam', 'mahendran', 'navaratnam', 'ponnambalam', 'rajendram',
        'sivakumar', 'shanmuganathan', 'paramanandam', 'thevarajah', 'saravanamuttu',
        'skandarajah', 'nadarajah', 'nadarajan', 'yogarajah', 'sivasubramaniam',
        'ratnavel', 'senathirajah', 'krishnarajan', 'murugaiah', 'rasaratnam',
        'sithamparanathan', 'velautham', 'kumarasamy', 'thiruchelvam', 'balasubramaniam',
        'ganeshpillai', 'sureshkumar', 'theivanayagam', 'rajagopalan', 'sundaram',
        'ravindran', 'maheswaran', 'karthigeyan', 'krishnapillai', 'kanapathipillai',
    }

    _SL_MUSLIM_SURNAMES = {
        'farook', 'hussain', 'rahman', 'nizam', 'abubacker', 'ismail', 'ibrahim',
        'saleem', 'hashim', 'naleer', 'rifai', 'markar', 'lebbe', 'baig',
        'sheriff', 'zarook', 'caffoor', 'thassim', 'razak', 'zubair',
        'mohideen', 'moulana', 'bawa', 'cassim', 'hadjiar', 'samsudeen',
        'fawmy', 'yusuf', 'ahamed', 'akbar', 'azeez', 'siddique', 'cader',
    }

    # Surname suffix patterns that strongly indicate SL origin
    _SINHALA_SUFFIXES = (
        'singhe', 'bandara', 'weera', 'sena', 'ratne', 'nayake', 'jayake',
        'wardena', 'sekera', 'warna', 'naike', 'kara', 'kumara', 'pakshe',
        'wansa', 'wansa', 'dena', 'ratna', 'suriya', 'sooriya',
    )
    _TAMIL_SUFFIXES = (
        'swamy', 'rajan', 'kumar', 'pillai', 'nair', 'krishnan', 'nathan',
        'samy', 'lingam', 'pathy', 'rajah', 'swami', 'murugan', 'param',
        'pakiam', 'rajam', 'arasam',
    )

    # Muslim first-name markers (prefix or standalone)
    _MUSLIM_GIVEN_PREFIXES = ('mohamed', 'mohammad', 'muhammad', 'muhammed', 'abdul',
                               'abul', 'abu', 'fathima', 'ayesha', 'ruqayyah')

    # ------------------------------------------------------------------
    # First-name gender lists
    # ------------------------------------------------------------------

    _SL_FEMALE_FIRST = {
        'oshadi', 'dilrukshi', 'nimesha', 'tharushi', 'sachini', 'sanduni',
        'thilini', 'nimasha', 'ishara', 'malsha', 'dinesha', 'kavindi',
        'ridma', 'hasini', 'hiruni', 'thisuri', 'amaya', 'navoda', 'dulani',
        'sithara', 'ruwangi', 'geethma', 'nethmi', 'piyumi', 'sulochana',
        'ramya', 'chathuri', 'rashmi', 'priyanka', 'chamari', 'upeksha',
        'kalpani', 'dilini', 'maduni', 'lakmali', 'nadeesha', 'devindi',
        'wasana', 'iresha', 'himasha', 'dulini', 'asanthi', 'madara',
        'vihanga', 'sewwandi', 'shenali', 'fathima', 'nilufar', 'anushka',
        'kavya', 'ishani', 'pooja', 'sumudu', 'harini', 'charuni',
        'dinusha', 'gayani', 'dewmini', 'shanika', 'bimba', 'dasuni',
        'malindi', 'pabasara', 'minudi', 'sarani', 'chathurika', 'kusali',
        'maneesha', 'nishadi', 'chanudi', 'yashodha', 'methma', 'thivanka',
        'ayasha', 'shehani', 'umayangana', 'ruvini', 'yolanda', 'sachindri',
        'ranmini', 'hasitha', 'dilnoza', 'nipunika', 'vinodha', 'chamindri',
    }

    _SL_MALE_FIRST = {
        'nuwan', 'kasun', 'thilan', 'chathura', 'dilshan', 'isuru', 'naveen',
        'lahiru', 'dinesh', 'roshan', 'chaminda', 'shanaka', 'malith', 'sahan',
        'nimesh', 'dushmantha', 'buddhika', 'ravindu', 'sithum', 'vimukthi',
        'supun', 'ashen', 'dhanushka', 'pulindu', 'shehan', 'pradeep',
        'nalin', 'ruchira', 'dasun', 'hirantha', 'thisara', 'udith', 'lakmal',
        'thushara', 'yoshitha', 'uvindu', 'dilan', 'sachith', 'charith',
        'krishan', 'mahesh', 'sumith', 'prasad', 'harsha', 'kavindu',
        'tharindu', 'randika', 'senura', 'dhananjaya', 'nipuna', 'gihan',
        'chiran', 'nimantha', 'deshan', 'ishan', 'sankalpa', 'amila',
        'thilina', 'thisath', 'udara', 'vinura', 'dmindu', 'sasith',
        'pasindu', 'janith', 'chalitha', 'ruvindra', 'oshadha', 'vidura',
        'harindra', 'kasuntha', 'ruchitha', 'chanaka', 'supantha', 'sampath',
        'malinga', 'priyankara', 'jayantha', 'chanitha', 'ravintha', 'sudath',
        'yohan', 'yasiru', 'dishan', 'dulith', 'dushyantha', 'sanjeewa',
    }

    _INTL_FEMALE_FIRST = {
        'emma', 'olivia', 'sophia', 'isabella', 'mia', 'charlotte', 'amelia',
        'harper', 'evelyn', 'abigail', 'emily', 'elizabeth', 'mila', 'ella',
        'victoria', 'madison', 'luna', 'grace', 'chloe', 'penelope', 'layla',
        'riley', 'zoey', 'nora', 'lily', 'eleanor', 'hannah', 'addison',
        'aubrey', 'ellie', 'stella', 'natalie', 'zoe', 'leah', 'hazel',
        'violet', 'aurora', 'savannah', 'audrey', 'brooklyn', 'bella',
        'claire', 'skylar', 'lucy', 'paisley', 'anna', 'caroline', 'nova',
        'emilia', 'kennedy', 'samantha', 'maya', 'willow', 'naomi', 'aaliyah',
        'elena', 'sarah', 'ariana', 'allison', 'mary', 'camila', 'alice',
        'avery', 'aria', 'scarlett', 'julia', 'nadia', 'margaret', 'jessica',
        'jennifer', 'ashley', 'amanda', 'stephanie', 'melissa', 'nicole',
        'kayla', 'rachel', 'danielle', 'heather', 'brittany', 'diana',
        'patricia', 'lisa', 'sandra', 'helen', 'karen', 'donna', 'carol',
        'ruth', 'catherine', 'deborah', 'virginia', 'pamela', 'martha',
        'judy', 'beverly', 'brenda', 'frances', 'jean', 'cheryl', 'janet',
        'jane', 'susan', 'linda', 'barbara', 'nancy', 'betty', 'dorothy',
        'rebecca', 'sharon', 'laurie', 'kimberly', 'diana', 'amy', 'ann',
    }

    _INTL_MALE_FIRST = {
        'james', 'john', 'robert', 'michael', 'william', 'david', 'richard',
        'joseph', 'thomas', 'charles', 'christopher', 'daniel', 'matthew',
        'anthony', 'mark', 'donald', 'steven', 'paul', 'andrew', 'joshua',
        'kenneth', 'kevin', 'brian', 'george', 'timothy', 'ronald', 'edward',
        'jason', 'jeffrey', 'ryan', 'jacob', 'gary', 'nicholas', 'eric',
        'jonathan', 'stephen', 'larry', 'justin', 'scott', 'brandon', 'frank',
        'benjamin', 'raymond', 'gregory', 'samuel', 'patrick', 'jack',
        'dennis', 'jerry', 'tyler', 'aaron', 'jose', 'henry', 'adam',
        'douglas', 'nathan', 'peter', 'zachary', 'kyle', 'noah', 'liam',
        'ethan', 'mason', 'oliver', 'elijah', 'aiden', 'lucas', 'logan',
        'alexander', 'caleb', 'sebastian', 'brayden', 'wyatt', 'julian',
        'grayson', 'leo', 'sawyer', 'dominic', 'xavier', 'carter', 'luke',
        'landon', 'eli', 'max', 'charlie', 'owen', 'jackson', 'gabriel',
        'christian', 'evan', 'nolan', 'ian', 'hunter', 'jordan', 'levi',
        'nathaniel', 'theo', 'harry', 'george', 'william', 'arthur', 'freddie',
    }

    # ------------------------------------------------------------------

    def classify(self, full_name: str) -> dict:
        """
        Classify a full name into cultural_origin and gender.

        Returns:
            dict with keys: cultural_origin, gender, confidence
        """
        parts = full_name.strip().split()
        if not parts:
            return {'cultural_origin': 'SL_SINHALA', 'gender': 'unknown', 'confidence': 0.0}

        first_name = parts[0].lower()
        last_name  = parts[-1].lower() if len(parts) > 1 else ''
        all_lower  = [p.lower() for p in parts]

        cultural_origin, origin_confidence = self._detect_origin(first_name, last_name, all_lower)
        gender,          gender_confidence  = self._detect_gender(first_name, cultural_origin)

        confidence = round((origin_confidence + gender_confidence) / 2, 2)
        return {
            'cultural_origin': cultural_origin,
            'gender':          gender,
            'confidence':      confidence,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _detect_origin(self, first: str, last: str, all_parts: list) -> tuple:
        """Returns (cultural_origin_str, confidence_float)."""

        # --- Muslim check first (any part can contain the signal) ---
        for part in all_parts:
            if part in self._SL_MUSLIM_SURNAMES:
                return 'SL_MUSLIM', 1.0
        for part in all_parts:
            if any(part.startswith(pfx) for pfx in self._MUSLIM_GIVEN_PREFIXES):
                return 'SL_MUSLIM', 0.95

        # --- Exact surname dictionary match ---
        if last in self._SL_SINHALA_SURNAMES:
            return 'SL_SINHALA', 1.0
        if last in self._SL_TAMIL_SURNAMES:
            return 'SL_TAMIL', 1.0

        # --- Suffix pattern match (weaker signal) ---
        if any(last.endswith(sfx) for sfx in self._SINHALA_SUFFIXES):
            return 'SL_SINHALA', 0.85
        if any(last.endswith(sfx) for sfx in self._TAMIL_SUFFIXES):
            return 'SL_TAMIL', 0.85

        # --- First-name dictionary match for SL origins (single-name case) ---
        if first in self._SL_FEMALE_FIRST or first in self._SL_MALE_FIRST:
            return 'SL_SINHALA', 0.7

        # --- Fallback: International ---
        return 'INTL', 0.6

    def _detect_gender(self, first: str, cultural_origin: str) -> tuple:
        """Returns (gender_str, confidence_float)."""

        if cultural_origin in ('SL_SINHALA', 'SL_TAMIL', 'SL_MUSLIM'):
            if first in self._SL_FEMALE_FIRST:
                return 'female', 1.0
            if first in self._SL_MALE_FIRST:
                return 'male', 1.0
            # Muslim-specific: fathima / ayesha are female
            if first in ('fathima', 'ayesha', 'ruqayyah', 'zainab', 'maryam'):
                return 'female', 0.95
            # Suffix heuristic for SL names
            if first.endswith('i') or first.endswith('a'):
                # Most SL female names end in 'i'; male names often end in 'a'
                # but it's ambiguous — use as a weak signal only
                return 'female', 0.6
            return 'unknown', 0.5

        # International
        if first in self._INTL_FEMALE_FIRST:
            return 'female', 1.0
        if first in self._INTL_MALE_FIRST:
            return 'male', 1.0

        return 'unknown', 0.5
