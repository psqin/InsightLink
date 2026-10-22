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
public class TeacherStudentMessage implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private Long senderId;

    private Long receiverId;

    private String content;

    private LocalDateTime sendTime;
}
