package com.psqin.domain.vo;

import com.fasterxml.jackson.annotation.JsonFormat;
import io.swagger.annotations.ApiModel;
import io.swagger.annotations.ApiModelProperty;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@ApiModel(description = "学生列表返回的数据")
public class StudentsPageVO {

    /**
     * StudentId
     */
    private Long id;

    private Long userId;

    private String studentNo;

    private String realName;

    private String avatar;

    private Integer gender;

    private String major;

    private String clazz;

    private Integer entryYear;

    @ApiModelProperty("绑定时间")
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime createTime;

}
