package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.entity.TeacherStudentMessage;
import com.psqin.domain.vo.UserVO;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 *
 */
@Mapper
public interface TsMessageMapper {

    Integer countTodayStudentMessages(@Param("teacherUserId") Long teacherUserId,
                                     @Param("beginTime") java.time.LocalDateTime beginTime,
                                     @Param("endTime") java.time.LocalDateTime endTime);

    void insert(TeacherStudentMessage teacherStudentMessage);

    List<UserVO> listContacts(@Param("userId") Long userId);

    Integer countConversation(@Param("userId") Long userId, @Param("otherUserId") Long otherUserId);

    Page<TeacherStudentMessage> pageHistory(@Param("userId") Long userId, @Param("otherUserId") Long otherUserId);
}
