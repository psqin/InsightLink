package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@ApiModel(description = "学生材料传递的数据模型")
public class StudentMaterialDTO {

    private Long id;

    /**
     * 材料类型：1-学习计划, 2-进度汇报, 3-自我总结
     */
    private Integer materialType;

    private String title;

    private String content;

    private String fileUrl;
}
