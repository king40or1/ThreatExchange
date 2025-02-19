# Copyright (c) Facebook, Inc. and its affiliates. All Rights Reserved

import bottle
from dataclasses import dataclass, asdict
from mypy_boto3_dynamodb.service_resource import Table
import typing as t
from enum import Enum
from threatexchange.descriptor import ThreatDescriptor

from hmalib.models import PDQMatchRecord, PDQSignalMetadata
from .middleware import jsoninator, JSONifiable


@dataclass
class MatchSummary(JSONifiable):
    content_id: str
    signal_id: t.Union[str, int]
    signal_source: str
    updated_at: str
    reactions: str

    def to_json(self) -> t.Dict:
        return asdict(self)


@dataclass
class MatchSummariesResponse(JSONifiable):
    match_summaries: t.List[MatchSummary]

    def to_json(self) -> t.Dict:
        return {
            "match_summaries": [summary.to_json() for summary in self.match_summaries]
        }


@dataclass
class MatchDetailMetadata(JSONifiable):
    dataset: str
    tags: t.List[str]
    opinion: str

    def to_json(self) -> t.Dict:
        return asdict(self)


@dataclass
class MatchDetail(JSONifiable):
    content_id: str
    content_hash: str
    signal_id: t.Union[str, int]
    signal_hash: str
    signal_source: str
    signal_type: str
    updated_at: str
    metadata: t.List[MatchDetailMetadata]

    def to_json(self) -> t.Dict:
        result = asdict(self)
        result.update(metadata=[datum.to_json() for datum in self.metadata])
        return result


@dataclass
class MatchDetailsResponse(JSONifiable):
    match_details: t.List[MatchDetail]

    def to_json(self) -> t.Dict:
        return {"match_details": [detail.to_json() for detail in self.match_details]}


def get_match_details(
    table: Table, content_id: str, image_folder_key: str
) -> t.List[MatchDetail]:
    if not content_id:
        return []

    records = PDQMatchRecord.get_from_content_id(
        table, f"{image_folder_key}{content_id}"
    )

    return [
        MatchDetail(
            content_id=record.content_id[len(image_folder_key) :],
            content_hash=record.content_hash,
            signal_id=record.signal_id,
            signal_hash=record.signal_hash,
            signal_source=record.signal_source,
            signal_type=record.SIGNAL_TYPE,
            updated_at=record.updated_at.isoformat(),
            metadata=get_signal_details(table, record.signal_id, record.signal_source),
        )
        for record in records
    ]


def get_signal_details(
    table: Table, signal_id: t.Union[str, int], signal_source: str
) -> t.List[MatchDetailMetadata]:
    if not signal_id or not signal_source:
        return []

    return [
        MatchDetailMetadata(
            dataset=metadata.ds_id,
            tags=[
                tag
                for tag in metadata.tags
                if tag
                not in [
                    ThreatDescriptor.TRUE_POSITIVE,
                    ThreatDescriptor.FALSE_POSITIVE,
                    ThreatDescriptor.DISPUTED,
                ]
            ],
            opinion=get_opinion_from_tags(metadata.tags).value,
        )
        for metadata in PDQSignalMetadata.get_from_signal(
            table, signal_id, signal_source
        )
    ]


class OpinionString(Enum):
    TP = "True Positive"
    FP = "False Positive"
    DISPUTED = "Unknown (Disputed)"
    UNKNOWN = "Unknown"


def get_opinion_from_tags(tags: t.List[str]) -> OpinionString:
    # see python-threatexchange descriptor.py for origins
    if ThreatDescriptor.TRUE_POSITIVE in tags:
        return OpinionString.TP
    if ThreatDescriptor.FALSE_POSITIVE in tags:
        return OpinionString.FP
    if ThreatDescriptor.DISPUTED in tags:
        return OpinionString.DISPUTED
    return OpinionString.UNKNOWN


def get_matches_api(dynamodb_table: Table, image_folder_key: str) -> bottle.Bottle:
    """
    A Closure that includes all dependencies that MUST be provided by the root
    API that this API plugs into. Declare dependencies here, but initialize in
    the root API alone.
    """

    # A prefix to all routes must be provided by the api_root app
    # The documentation below expects prefix to be '/matches/'
    matches_api = bottle.Bottle()

    @matches_api.get("/", apply=[jsoninator])
    def matches() -> MatchSummariesResponse:
        """
        Returns all, or a filtered list of matches.
        """
        signal_q = bottle.request.query.signal_q or None
        signal_source = bottle.request.query.signal_source or None
        content_q = bottle.request.query.content_q or None

        if content_q:
            records = PDQMatchRecord.get_from_content_id(dynamodb_table, content_q)
        elif signal_q:
            records = PDQMatchRecord.get_from_signal(
                dynamodb_table, signal_q, signal_source or ""
            )
        else:
            records = PDQMatchRecord.get_from_time_range(dynamodb_table)

        return MatchSummariesResponse(
            match_summaries=[
                MatchSummary(
                    content_id=record.content_id[len(image_folder_key) :],
                    signal_id=record.signal_id,
                    signal_source=record.signal_source,
                    updated_at=record.updated_at.isoformat(),
                    reactions="Mocked",
                )
                for record in records
            ]
        )

    @matches_api.get("/match/<key>/", apply=[jsoninator])
    def match_details(key=None) -> MatchDetailsResponse:
        """
        matche details API endpoint:
        return format: match_details : [MatchDetailsResult]
        """
        results = get_match_details(dynamodb_table, key, image_folder_key)
        return MatchDetailsResponse(match_details=results)

    return matches_api
