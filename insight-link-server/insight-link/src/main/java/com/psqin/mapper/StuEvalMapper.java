package com.psqin.mapper;

import com.psqin.domain.entity.StudentEvaluation;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Update;

/**
 *
 */
@Mapper
public interface StuEvalMapper {
    void insert(StudentEvaluation studentEvaluation);

    @Select("select count(*) from student_evaluation where material_id = #{materialId}")
    Integer countByMaterialId(Long materialId);

    @Delete("delete from student_evaluation where material_id = #{materialId}")
    void deleteByMaterialId(Long materialId);

    @Delete("delete from student_evaluation where id = #{id}")
    void deleteById(Long id);

    void update(StudentEvaluation studentEvaluation);

    @Select("select * from student_evaluation where id = #{id}")
    StudentEvaluation getById(Long id);

    @Select("select count(*) from student_evaluation")
    Integer countAll();

    @Select("select round(avg(score), 2) from student_evaluation")
    java.math.BigDecimal avgScore();

    @Select("select date(evaluation_time) as day, count(*) as count from student_evaluation where evaluation_time >= #{startTime} group by date(evaluation_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCount(@org.apache.ibatis.annotations.Param("startTime") java.time.LocalDateTime startTime);

    @Select("select count(*) from student_evaluation where teacher_user_id = #{teacherUserId}")
    Integer countByTeacherUserId(@org.apache.ibatis.annotations.Param("teacherUserId") Long teacherUserId);

    @Select("select round(avg(score), 2) from student_evaluation where teacher_user_id = #{teacherUserId}")
    java.math.BigDecimal avgScoreByTeacherUserId(@org.apache.ibatis.annotations.Param("teacherUserId") Long teacherUserId);

    @Select("select date_format(evaluation_time, '%Y-%m-%d') as day, count(*) as count from student_evaluation where teacher_user_id = #{teacherUserId} and evaluation_time >= #{startTime} group by date_format(evaluation_time, '%Y-%m-%d') order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCountByTeacherUserId(@org.apache.ibatis.annotations.Param("teacherUserId") Long teacherUserId,
                                                                                  @org.apache.ibatis.annotations.Param("startTime") java.time.LocalDateTime startTime);
}
