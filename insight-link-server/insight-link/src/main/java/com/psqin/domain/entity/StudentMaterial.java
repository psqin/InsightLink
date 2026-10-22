package com.psqin.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.time.LocalDateTime;

/**
 *
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudentMaterial implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private Long studentUserId;

    /**
     * 材料类型：1-学习计划, 2-进度汇报, 3-自我总结
     */
    private Integer materialType;

    private String title;

    private String content;

    private String fileUrl;

    private LocalDateTime submitTime;
}
