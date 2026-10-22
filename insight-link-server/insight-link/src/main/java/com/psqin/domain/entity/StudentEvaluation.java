package com.psqin.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;
import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 *
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class StudentEvaluation implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private Long materialId;

    /**
     * 评分：0-100分
     */
    private BigDecimal score;

    private String content;

    private LocalDateTime evaluationTime;

    private Long teacherUserId;
}
