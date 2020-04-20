[Workshop](../../README.md) | [Lab 0](../../Lab0/README.md) | [Lab 1](../../Lab1/README.md) | [Lab 2](../../Lab2/README.md)

# LAB 3 - Asynchronous - Index documents and entities in Elasticsearch

[Amazon Elasticsearch Service](https://aws.amazon.com/elasticsearch-service) is a managed Elasticsearch, the famous search engine based on Lucene library. It enables the indexing of billions of documents and offers near real-time search from those documents. In this lab, we will use it to store the content of our scanned documents and associated entities.

## Elasticsearch & Kibana
We first need to setup an Elasticsearch *domain* (a cluster) and secure the Kibana console with Cognito. The following Cloudformation template will setup everything for you. Just type your email address (use a valid address you can access) and a name for the domain when prompted. 

Region | Button
------------ | -------------
us-east-1 | [![Launch stack in us-east-1](../../images/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home?region=us-east-1#/stacks/new?stackName=DocumentIndexingStack&templateURL=https://s3.amazonaws.com/aws-textract-workshop-us-east-1/bootstrap/es-template.yaml)
eu-west-1 | [![Launch stack in eu-west-1](../../images/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home?region=eu-west-1#/stacks/new?stackName=DocumentIndexingStack&templateURL=https://s3.amazonaws.com/aws-textract-workshop-eu-west-1/bootstrap/es-template.yaml)
ap-southeast-1 | [![Launch stack in ap-southeast-1](../../images/launch-stack.svg)](https://console.aws.amazon.com/cloudformation/home?region=ap-southeast-1#/stacks/new?stackName=DocumentIndexingStack&templateURL=https://s3.amazonaws.com/aws-textract-workshop-ap-southeast-1/bootstrap/es-template.yaml)

In the last step, you will need to check several checkboxes to allow the creation of IAM resources:

![Capabilities](../../synchronous/Lab3/images/cloudformation.png)

It may take few minutes to deploy everything (you can have a look at the rest of the lab but you will need resources to be ready to complete it). In the [CloudFormation Console](https://console.aws.amazon.com/cloudformation/home), in Outputs tab, you should have the following. Keep these information in safe place for later use (copy past in text document or keep browser tab opened). You should also receive an email with a password to access the Kibana interface.

![CloudFormation outputs for Elasticsearch and Role](../../synchronous/Lab3/images/escloudformation.png)

More details on Cognito authentication for Kibana [here](https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/es-cognito-auth.html).

## Architecture
![Asynchronous Architecture](images/es_async_archi.png)

In this lab, we will focus on step 9, in which we will index the data in ElasticSearch. See labs [1](../Lab1/README.md#archi_async) and [2](../Lab2/README.md#archi_async) for the previous steps.

## Dependencies for the lambda function
As the function will interact with ElasticSearch, we need to provide some libraries. We'll do that using a layer. In [Lambda](https://console.aws.amazon.com/lambda/home), click on your *documentAnalysis* function then click on **Layers** and **Add a layer**:

![Layer](images/layer.png)

In the new window, select the **"ElasticLibs"** layer, click **Add** and don't forget to **Save** the Lambda.

We'll also need to provide the URL of the ElasticSearch Domain. Scroll down to **Environment variables** and add the following variable (key: ELASTIC_SEARCH_HOST, value: put the URL you got from CloudFormation):

![Environment](../../synchronous/Lab3/images/lambda_var_es_host.png)

## Permissions
The function needs permissions to access ElasticSearch. As mentioned above, the domain is currently protected with Cognito. Go to [ElasticSearch service console](https://console.aws.amazon.com/es/home), select your domain, then click on **Modify access policy**

![Elasticsearch console](../../synchronous/Lab3/images/es_console.png)

In the policy editor, we will add permissions (`es:ESHttpPost`) for the Lambda execution role. Add the following block of JSON to the existing one (within the *Statement* array:

```json
, 
   {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:role/textract-index-stack-LambdaExecutionRole-12A34B56D78E"
      },
      "Action": "es:ESHttpPost",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/apollodocumentsearch/*"
    }
```

a. Replace AWS principal ARN value with the one from your Lambda function. You can find it in your lambda function by clicking the  **View the TextractApolloWorkshopStack-....** link:

![Lambda execution role](../../synchronous/Lab3/images/role_lambda.png)

b. Change the "111111111" with your account ID (you can see it in the JSON block already available).

c. Replace "apollodocumentsearch" with the name of your Elasticsearch domain created in the stack (see Cloudformation outputs).

At the end, you should have something like that (with your own values), **do not** copy past this block:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:sts::111111111111:assumed-role/es-stack-CognitoAuthorizedRole-1AB2CD3EF4GH/CognitoIdentityCredentials"
      },
      "Action": "es:*",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/apollodocumentsearch/*"
    },
    {
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::111111111111:role/textract-index-stack-LambdaExecutionRole-12A34B56D78E"
      },
      "Action": "es:ESHttpPost",
      "Resource": "arn:aws:es:us-east-1:111111111111:domain/apollodocumentsearch/*"
    }
  ]
}
```
Click **Submit** on the bottom right of the page and wait few seconds so it is taken into account (Domain status needs to be "Active" again).

## Update the documentAnalysis code

Back to your *documentAnalysis* function Lambda function, in the inline code editor, click **File**, **New file** and paste the following code:

```python
import boto3
import urllib
import os
import requests
from requests_aws4auth import AWS4Auth

region = os.environ["AWS_REGION"]
service = "es"
credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key,
                   credentials.secret_key,
                   region,
                   service,
                   session_token=credentials.token)

elastic_search_host = os.environ["ELASTIC_SEARCH_HOST"]
index = "documents"
type = "doc"
headers = {"Content-Type": "application/json"}
elastic_url = elastic_search_host + index + '/' + type


class DocumentIndexer():
    def index(self, document):
        """ Index the full document (pages and entities) in elasticsearch """

        response = requests.post(elastic_url,
                                 auth=awsauth,
                                 json=document,
                                 headers=headers)
        response.raise_for_status()

        es_response = response.json()
        return es_response["_id"]

```

Few things to notice:

- This class is dedicated to the indexation of the analyzed document. We will use it in the main lambda function.

- We could also use the [Elasticsearch library](https://elasticsearch-py.readthedocs.io/en/master/) but as we only do an HTTP POST, we keep it simple and use the [Python's Requests Library](https://requests.readthedocs.io/en/latest/).

- We then use the [Signature v4](https://docs.aws.amazon.com/general/latest/gr/signing_aws_api_requests.html) (`AWS4Auth`) to add `Authorization` headers to the HTTP request.

- We retrieve the environment variable containing the Elasticsearch domain URL (`os.environ[""]`) and build the URL of the index.

- The rest is pretty straightforward, we do an HTTP POST with the appropriate parameters: URL, authorizations, headers and the document itself. 


Once you're comfortable with the code, click **File**, **Save**, and use *document_indexer.py* as filename.

In the *lambda_function.py* file, add the following code at the top:

```python
from document_indexer import DocumentIndexer
document_indexer = DocumentIndexer()
```

And the following one at the end of the lambda_handler function:

```python
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
```

Here we build the document that will be indexed: json object containing information regarding the document (bucket and object), the extracted text (pages) and entities found by Comprehend, and finally we index it.

Hit **Save** in the top right corner of the screen and then click **Test**. Observe the result in [CloudWatch logs](https://console.aws.amazon.com/cloudwatch/home#logs:prefix=/aws/lambda/documentAnalysis).

Then open the url of Kibana (provided in Cloudformation outputs). You will need the password received by email to log on (final dot in the email is not part of the password). Your username is your email address. After the first login to Kibana, You will be asked to change your password.

Click on **Discover** on upper left, you will be asked to create an index pattern (type "documents", then go to **Next step** and validate): 
![Kibana index pattern](../../synchronous/Lab3/images/kibana_index_pattern_async.png)

If you go back to **Discover** on upper left, you should be able to see the content of the document you've just pushed to S3, plus the different entities and some metadata:

![Kibana](images/kibana_result_async.png)

You can also see a search bar and use it with the query language to search for something:

![Kibana search](../../synchronous/Lab3/images/es_search.png)

You can also upload one of the [documents](../../documents/) and see the same result.

Congratulations! The full process is done: 

- The content has been extracted by Amazon Textract, 
- Amazon Comprehend extracted the entities,
- And Amazon Elasticsearch Service indexed it

Once your data is indexed in Elasticsearch, you can create any kind of application that will search data in it.

## Exploring further options

In this workshop, we mainly worked with 3 services (Amazon Textract, Amazon Comprehend and Amazon Elasticsearch Service) but you could leverage other services to add more features:

- [Amazon Rekognition](https://aws.amazon.com/rekognition/) to extract information about pictures in the documents.
- [Amazon Kendra](https://aws.amazon.com/kendra/) instead of / in addition to Elasticsearch to enable search using natural language.
- [Amazon Polly](https://aws.amazon.com/polly/) to generate speech from extracted text.
- [AWS Step Functions](https://aws.amazon.com/step-functions/) to manage the (now) increasing complexity of the workflow.

## Cleanup

[Clean your resources](../../README.md#cleanup)
