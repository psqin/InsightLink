package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.vo.StudentsPageVO;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface TsGuidanceMapper {
    /**
     *
     * @param ids 学生用户id
     * @param teacherId 导师用户id
     */
    void saveByIds(@Param("ids") List<Long> ids, @Param("teacherId") Long teacherId);

    void deleteByIds(@Param("ids") List<Long> ids, @Param("teacherId") Long teacherId);

    /**
     * 查询导师绑定的学生
     * @param studentSearchDTO
     * @param teacherId
     * @return
     */
    Page<StudentsPageVO> pageQuery(@Param("dto") StudentSearchDTO studentSearchDTO, @Param("teacherId") Long teacherId);

    /**
     * 检查是否绑定
     * @param teacherId
     * @param studentUserId
     * @return
     */
    Integer countByTeacherAndStudent(@Param("teacherId") Long teacherId, @Param("studentUserId") Long studentUserId);

    List<Long> listStudentUserIdsByTeacherAndStudentIds(@Param("teacherId") Long teacherId, @Param("studentIds") List<Long> studentIds);

    Long getTeacherUserIdByStudentUserId(@Param("studentUserId") Long studentUserId);

    /**
     * 根据学生用户ID删除绑定关系
     * @param studentUserId
     */
    @Delete("delete from ts_guidance where student_user_id = #{studentUserId}")
    void deleteByStudentUserId(Long studentUserId);

    /**
     * 根据导师用户ID删除绑定关系
     * @param teacherUserId
     */
    @Delete("delete from ts_guidance where teacher_user_id = #{teacherUserId}")
    void deleteByTeacherUserId(Long teacherUserId);

    @org.apache.ibatis.annotations.Select("select count(*) from ts_guidance")
    Integer countAll();

    @org.apache.ibatis.annotations.Select("select date(create_time) as day, count(*) as count from ts_guidance where create_time >= #{startTime} group by date(create_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCount(@org.apache.ibatis.annotations.Param("startTime") java.time.LocalDateTime startTime);

    @org.apache.ibatis.annotations.Select("select count(*) from ts_guidance where teacher_user_id = #{teacherUserId}")
    Integer countByTeacherUserId(@org.apache.ibatis.annotations.Param("teacherUserId") Long teacherUserId);
}
