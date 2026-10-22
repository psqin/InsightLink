package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import lombok.Data;

/**
 *
 */
@Data
@ApiModel(description = "发消息的数据模型")
public class TsMessageDTO {

    private Long receiverId;

    private String content;
}
