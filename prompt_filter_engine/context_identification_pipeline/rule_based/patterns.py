# Rule-based patterns
EMAIL_PATTERNS = {
    'gov': r'\.gov\.',
    'edu': r'\.(edu|ac\.lk)',
    'work': r'\.(com|org|net|lk)',
}

PHONE_PATTERNS = {
    'sl_mobile': r'^(\+94|0)?7[0-9]{8}$',
    'sl_landline': r'^(\+94|0)?[1-9][0-9]{8}$',
    'international': r'^\+(?!94)'
}

SSN_PATTERNS = {
    'us': r'^\d{3}-\d{2}-\d{4}$'
}

DL_PATTERNS = {
    'sl_old': r'^[A-Z]\d{7}$',
    'sl_new': r'^[A-Z]{2}\d{8}$',
    'international': r'^[A-Z0-9\-]+$'
}
