package com.psqin.domain.entity;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.io.Serializable;

/**
 *
 */
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Teachers implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private Long userId;

    private String teacherNo;

    private Long universityId;

    /**
     * 所属院系ID（关联sys_dept表，dept_type=1）
     */
    private Long deptId;

    private String title;

    private String researchField;

}
