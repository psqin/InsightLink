package com.psqin.service;

import com.psqin.domain.dto.TsMessageDTO;
import com.psqin.domain.entity.TeacherStudentMessage;
import com.psqin.domain.vo.UserVO;
import com.psqin.result.PageResult;

import java.util.List;

/**
 *
 */
public interface TsMessageService {
    void save(TsMessageDTO tsMessageDTO);

    List<UserVO> listContacts();

    PageResult pageHistory(Long otherUserId, Integer page, Integer pageSize);
}
