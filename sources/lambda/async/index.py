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
import json
from text_extractor import TextExtractor
from document_analyzer import DocumentAnalyzer
from document_indexer import DocumentIndexer

document_indexer = DocumentIndexer()
document_analyzer = DocumentAnalyzer()
text_extractor = TextExtractor()


def handler(event, context):
    message = json.loads(event['Records'][0]['Sns']['Message'])

    jobId = message['JobId']
    print("JobId="+jobId)

    status = message['Status']
    print("Status="+status)

    if status != "SUCCEEDED":
        return {
            # TODO : handle error with Dead letter queue (not in this workshop)
            # https://docs.aws.amazon.com/lambda/latest/dg/dlq.html
            "status": status
        }

    pages = text_extractor.extract_text(jobId)
    print(list(pages.values()))

    entities = document_analyzer.extract_entities(list(pages.values()))
    print(entities)

    doc = {
        "bucket": message['DocumentLocation']['S3Bucket'],
        "document": message['DocumentLocation']['S3ObjectName'],
        "size": len(list(pages.values())),
        "jobId": jobId,
        "pages": list(pages.values()),
        "entities": entities
    }

    print(doc)

    docId = document_indexer.index(doc)

    return {
        "jobId": jobId,
        "docId": docId
    }
