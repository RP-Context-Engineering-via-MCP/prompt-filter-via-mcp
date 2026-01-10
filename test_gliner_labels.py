from gliner import GLiNER

def test_labels():
    model = GLiNER.from_pretrained("urchade/gliner_medium-v2.1")
    text = "Kamal Perera is a 34-year-old individual living at No. 102, Lake View Road, Nawala, Sri Lanka. He can be reached via the phone number +94 77 456 7890 or through the"
    
    labels = ["address", "country", "location", "city"]
    
    print(f"Testing labels: {labels}")
    entities = model.predict_entities(text, labels, threshold=0.3)
    
    for entity in entities:
        print(f"Label: {entity['label']}, Text: '{entity['text']}'")

if __name__ == "__main__":
    test_labels()
