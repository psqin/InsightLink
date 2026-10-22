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
public class SystemNotice implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private String title;

    private String content;

    private Long publisherId;

    private LocalDateTime publishTime;

    /**
     * 通知类型：1-系统通知（管理员发布）, 2-导师通知（导师发布给绑定学生）
     */
    private Integer type;
}
