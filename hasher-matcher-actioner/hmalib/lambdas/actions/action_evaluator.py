# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved

import boto3
import json
import os
import typing as t

from dataclasses import dataclass, field
from functools import lru_cache
from hmalib.common.logging import get_logger
from hmalib.models import MatchMessage
from hmalib.common.actioner_models import (
    Action,
    ActionLabel,
    ActionMessage,
    ActionRule,
    Label,
    ReactionMessage,
    ThreatExchangeReactionLabel,
)
from hmalib.lambdas.actions.action_performer import perform_label_action

logger = get_logger(__name__)
sqs_client = boto3.client("sqs")


@dataclass
class ActionEvaluatorConfig:
    """
    Simple holder for getting typed environment variables
    """

    actions_queue_url: str
    reactions_queue_url: str

    @classmethod
    @lru_cache(maxsize=1)
    def get(cls):
        return cls(
            actions_queue_url=os.environ["ACTIONS_QUEUE_URL"],
            reactions_queue_url=os.environ["REACTIONS_QUEUE_URL"],
        )


def lambda_handler(event, context):
    """
    This lambda is called when one or more matches are found. If a single hash matches
    multiple datasets, this will be called only once.

    Action labels are generated for each match message, then an action is performed
    corresponding to each action label.
    """
    config = ActionEvaluatorConfig.get()

    for sqs_record in event["Records"]:
        # TODO research max # sqs records / lambda_handler invocation
        sqs_record_body = json.loads(sqs_record["body"])
        match_message = MatchMessage.from_aws_message(sqs_record_body["Message"])

        logger.info("Evaluating match_message: %s", match_message)

        action_labels = get_action_labels(match_message)
        for action_label in action_labels:
            action_message = ActionMessage.from_match_message_and_label(
                match_message, action_label
            )
            sqs_client.send_message(
                QueueUrl=config.actions_queue_url,
                MessageBody=json.dumps(action_message.to_aws_message()),
            )

        if threat_exchange_reacting_is_enabled(match_message):
            threat_exchange_reaction_labels = get_threat_exchange_reaction_labels(
                match_message, action_labels
            )
            if threat_exchange_reaction_labels:
                for threat_exchange_reaction_label in threat_exchange_reaction_labels:
                    threat_exchange_reaction_message = (
                        ReactionMessage.from_match_message_and_label(
                            match_message, threat_exchange_reaction_label
                        )
                    )
                    sqs_client.send_message(
                        QueueUrl=config.reactions_queue_url,
                        MessageBody=json.dumps(
                            threat_exchange_reaction_message.to_aws_message()
                        ),
                    )

    return {"evaluation_completed": "true"}


def get_action_labels(match_message: MatchMessage) -> t.List["ActionLabel"]:
    """
    TODO finish implementation
    Returns an ActionLabel for each ActionRule that applies to a MatchMessage.
    """
    action_rules = get_action_rules()
    action_labels: t.List["ActionLabel"] = []
    for action_rule in action_rules:
        if action_rule_applies_to_match_message(
            action_rule, match_message
        ) and not action_labels.__contains__(action_rule.action_label):
            action_labels.append(action_rule.action_label)
    action_labels = remove_superseded_actions(action_labels)
    return action_labels


def get_action_rules() -> t.List["ActionRule"]:
    """
    TODO implement
    Returns the ActionRule objects stored in the config repository. Each ActionRule
    will have the following attributes: MustHaveLabels, MustNotHaveLabels, ActionLabel.
    """
    return [
        ActionRule(
            ActionLabel("EnqueueForReview"),
            [Label("Collaboration", "12345")],
            [],
        )
    ]


def action_rule_applies_to_match_message(
    action_rule: ActionRule, match_message: MatchMessage
) -> bool:
    """
    Evaluate if the action rule applies to the match message. Return True if the action rule's "must have"
    labels are all present in the match message, and that none of the "must not have" labels are present
    in the match message, otherwise return False.
    """
    return True


def get_actions() -> t.List[Action]:
    """
    TODO implement
    Returns the Action objects stored in the config repository. Each Action will have
    the following attributes: ActionLabel, Priority, SupersededByActionLabel (Priority
    and SupersededByActionLabel are used by remove_superseded_actions).
    """
    return [
        Action(
            ActionLabel("ENQUEUE_FOR_REVIEW"),
            1,
            [ActionLabel("A_MORE_IMPORTANT_ACTION")],
        )
    ]


def remove_superseded_actions(
    action_labels: t.List["ActionLabel"],
) -> t.List[ActionLabel]:
    """
    TODO implement
    Evaluates a collection of ActionLabels generated for a match message against the actions.
    Action labels that are superseded by another will be removed.
    """
    return action_labels


def threat_exchange_reacting_is_enabled(match_message: MatchMessage) -> bool:
    """
    TODO implement
    Looks up from a config whether ThreatExchange reacting is enabled. Initially this will be a global
    config, and this method will return True if reacting is enabled, False otherwise. At some point the
    config for reacting to ThreatExchange may be on a per collaboration basis. In that case, the config
    will be referenced for each collaboration involved (implied by the match message). If reacting
    is enabled for a given collaboration, a label will be added to the match message
    (e.g. "ThreatExchangeReactingEnabled:<collaboration-id>").
    """
    return True


def get_threat_exchange_reaction_labels(
    match_message: MatchMessage,
    action_labels: t.List[ActionLabel],
) -> t.List[Label]:
    """
    TODO implement
    Evaluates a collection of action_labels against some yet to be defined configuration
    (and possible business login) to produce
    """
    return [ThreatExchangeReactionLabel("SAW_THIS_TOO")]


if __name__ == "__main__":
    # For basic debugging
    match_message = MatchMessage("key", "hash", [])
    action_label = ActionLabel("ENQUE_FOR_REVIEW")
