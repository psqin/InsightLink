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
public class SysDept implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private String name;

    /**
     * 部门类型：1-院系, 2-专业, 3-班级
     */
    private Integer deptType;

    /**
     * 父级ID：院系为NULL，专业父级=院系ID，班级父级=专业ID
     */
    private Long parentId;

    private Long universityId;

    private String universityName;

    private String parentName;
}
