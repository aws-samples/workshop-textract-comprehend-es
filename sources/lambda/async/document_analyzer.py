import boto3

comprehend = boto3.client('comprehend')
translate = boto3.client('translate')


class DocumentAnalyzer():
    def extract_entities(self, pages):
        """ extract entities from pages with Comprehend """

        selected_entity_types = ["ORGANIZATION", "PERSON", "LOCATION", "DATE"]

        final_entities = []
        for page in pages:
            text = self.__get_clean_text_in_supported_language(page['Content'])

            detected_entities = comprehend.detect_entities(
                Text=text,
                LanguageCode="en"
            )

            # uncomment to see output of comprehend
            # print(detected_entities)

            selected_entities = [x for x in detected_entities['Entities']
                                 if x['Score'] > 0.9 and
                                 x['Type'] in selected_entity_types]

            for selected_entity in selected_entities:
                clean_entity = {key: selected_entity[key]
                                for key in ["Text", "Type"]}
                if clean_entity not in final_entities:
                    final_entities.append(clean_entity)

        return final_entities

    def __get_clean_text_in_supported_language(self, inputText):
        """ Prepare text for Comprehend:
        reduce the size of the text to 5000 bytes
        and translate it in english if not in supported language """

        # max size for Comprehend: 5000 bytes
        text = inputText[:5000]

        languages = comprehend.detect_dominant_language(
            Text=text
        )
        dominant_languages = sorted(languages['Languages'],
                                    key=lambda k: k['LanguageCode'])
        dominant_language = dominant_languages[0]['LanguageCode']

        if dominant_language not in ['en', 'es', 'fr', 'de', 'it', 'pt']:
            translation = translate.translate_text(
                Text=text,
                SourceLanguageCode=dominant_language,
                TargetLanguageCode="en"
            )
            text = translation['TranslatedText']

        return text[:5000]
