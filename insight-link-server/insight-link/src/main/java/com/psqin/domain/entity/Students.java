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
public class Students implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;

    private Long userId;

    private String studentNo;

    private Long universityId;

    private Long collegeId;

    private Long majorId;

    private Long classId;

    private Integer entryYear;

    /**
     * 0 未绑定，1 已绑定
     */
    private Integer bindStatus;

}
