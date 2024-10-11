provider "aws" {
    region = "us-east-1"  
  }
  
  resource "aws_sns_topic" "ses_bounce_topic" {
    name = "ses-bounce-topic"
  }
  
  resource "aws_sns_topic_subscription" "ses_bounce_email_subscription" {
    topic_arn = aws_sns_topic.ses_bounce_topic.arn
    protocol  = "email"
    endpoint  = "tony.cannistra+avymailnotifications@gmail.com" 
  }
  
  resource "aws_ses_identity_notification_topic" "ses_complaint_notification" {
    identity          = "forecast@avy.email" 
    notification_type = "Complaint"
    topic_arn         = aws_sns_topic.ses_bounce_topic.arn
  }


  resource "aws_ses_identity_notification_topic" "ses_bounce_notification" {
    identity          = "forecast@avy.email" 
    notification_type = "Bounce"
    topic_arn         = aws_sns_topic.ses_bounce_topic.arn
  }
  
  resource "aws_ses_receipt_rule_set" "default" {
    rule_set_name = "default-rule-set"
  }
  
  resource "aws_ses_receipt_rule" "bounce_rule" {
    name          = "BounceRule"
    rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
    enabled       = true
    recipients    = ["forecast@avy.email"] 
  

    sns_action {
        topic_arn = aws_sns_topic.ses_bounce_topic.arn
        position = 1
    }

  
    scan_enabled = true
  }

  resource "aws_ses_receipt_rule" "complaint_rule" {
    name          = "ComplaintRule"
    rule_set_name = aws_ses_receipt_rule_set.default.rule_set_name
    enabled       = true
    recipients    = ["forecast@avy.email"]  
  

    sns_action {
        topic_arn = aws_sns_topic.ses_bounce_topic.arn
        position = 1
    }

  
    scan_enabled = true
  }