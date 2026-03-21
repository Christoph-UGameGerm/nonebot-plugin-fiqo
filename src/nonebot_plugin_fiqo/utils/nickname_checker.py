from collections import defaultdict
from collections.abc import Sequence

from nonebot_plugin_fiqo.config import plugin_config
from nonebot_plugin_fiqo.models import UserAndCompanyDTO


def analyze_nickname_entities(
    service_result: Sequence[tuple[str, list[tuple[str, UserAndCompanyDTO | None]]]],
) -> tuple[UserAndCompanyDTO | None, list[str]]:
    entity_score: dict[str, int] = defaultdict(int)
    entity_map: dict[str, UserAndCompanyDTO] = {}

    declared_faction = None
    for token, identities in service_result:
        if any(label == "派系" for label, _ in identities):
            declared_faction = plugin_config.game.all_ingame_fas.get(token)
            break

    for _, identities in service_result:
        unique_dtos = {dto.user_id: dto for _, dto in identities if dto}

        for uid, dto in unique_dtos.items():
            entity_score[uid] += 1
            entity_map[uid] = dto
            if declared_faction and dto.faction == declared_faction:
                entity_score[uid] += 1

    best_dto = None
    if entity_score:
        best_entity_id = max(entity_score, key=entity_score.__getitem__)
        best_dto = entity_map[best_entity_id]

    report_lines = []
    for token, identities in service_result:
        is_faction = any(label == "派系" for label, _ in identities)

        winning_labels = [
            label
            for label, dto in identities
            if best_dto and dto and dto.user_id == best_dto.user_id
        ]

        if is_faction:
            final_label = "派系"
        elif winning_labels:
            final_label = "/".join(winning_labels)
        else:
            final_label = "未知"

        report_lines.append(f"- 字段 '{token}' 指向信息：{final_label}")

    return best_dto, report_lines
