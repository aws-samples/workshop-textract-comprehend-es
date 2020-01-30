#
# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
import urllib
import boto3

import os
import requests
from requests_aws4auth import AWS4Auth

region = os.environ['AWS_REGION']
service = 'es'
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key,
                   credentials.secret_key,
                   region,
                   service,
                   session_token=credentials.token)
elastic_search_host = os.environ["ELASTIC_SEARCH_HOST"]
index = "docs"
type = "doc"
headers = {"Content-Type": "application/json"}
elastic_url = elastic_search_host + index + '/' + type

textract = boto3.client('textract')
comprehend = boto3.client('comprehend')


def handler(event, context):
    source_bucket = event['Records'][0]['s3']['bucket']['name']
    object_key = urllib.parse.unquote_plus(
                         event['Records'][0]['s3']['object']['key'])

    textract_result = textract.detect_document_text(
        Document={
            'S3Object': {
                'Bucket': source_bucket,
                'Name': object_key
            }
        }
    )
    page = ""
    blocks = [x for x in textract_result['Blocks']
              if x['BlockType'] == "LINE"]
    for block in blocks:
        page += " " + block['Text']

    text = page[:5000]

    languages = comprehend.detect_dominant_language(
        Text=text
    )
    dominant_languages = sorted(languages['Languages'],
                                key=lambda k: k['LanguageCode'])
    dominant_language = dominant_languages[0]['LanguageCode']
    if dominant_language not in ['en', 'es', 'fr', 'de', 'it', 'pt']:
        # TODO (optional): call Amazon translate to get it in english
        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/translate.html#Translate.Client.translate_text
        dominant_language = "en"

    detected_entities = comprehend.detect_entities(
        Text=text,
        LanguageCode=dominant_language
    )
    selected_entity_types = ["ORGANIZATION", "PERSON", "LOCATION", "DATE"]
    selected_entities = [x for x in detected_entities['Entities']
                         if x['Score'] > 0.9 and
                         x['Type'] in selected_entity_types]

    doc = {
        "bucket": source_bucket,
        "document": object_key,
        "content": page,
        "entities": selected_entities
    }

    response = requests.post(elastic_url,
                             auth=awsauth,
                             json=doc,
                             headers=headers)
    response.raise_for_status()

    es_response = response.json()
    print(es_response)
    return es_response["_id"]
