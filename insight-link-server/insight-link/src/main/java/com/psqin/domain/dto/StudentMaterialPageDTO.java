package com.psqin.domain.dto;

import io.swagger.annotations.ApiModel;
import lombok.Data;
import java.io.Serializable;

@Data
@ApiModel(description = "学生材料分页查询数据模型")
public class StudentMaterialPageDTO implements Serializable {

    private int page = 1;

    private int pageSize = 10;

    private Integer materialType;

    private String title;
}
