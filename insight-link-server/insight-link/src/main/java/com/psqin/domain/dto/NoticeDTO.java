package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import lombok.Data;

import java.time.LocalDateTime;

/**
 *
 */
@Data
@ApiModel(description = "通知的数据模型")
public class NoticeDTO {

    private String title;

    private String content;

}
