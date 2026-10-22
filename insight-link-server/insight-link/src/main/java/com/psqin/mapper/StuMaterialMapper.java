package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.entity.StudentMaterial;
import com.psqin.domain.dto.StuMatTeaSearchPageDTO;
import com.psqin.domain.vo.StudentMaterialVO;
import com.psqin.domain.vo.StuMaterialPageVO;
import org.apache.ibatis.annotations.Delete;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;

import java.util.List;

@Mapper
public interface StuMaterialMapper {
    @Insert("insert into student_material (student_user_id, material_type, title, content, file_url) " +
            "values" +
            " (#{studentUserId}, #{materialType}, #{title}, #{content}, #{fileUrl})")
    void insert(StudentMaterial studentMaterial);

    @Select("select sm.*, (case when se.id is null then 0 else 1 end) as evaluated, se.id as evaluation_id, se.score, se.content as evaluation_content, se.evaluation_time, se.teacher_user_id, u.real_name as teacher_real_name " +
            "from student_material sm " +
            "left join student_evaluation se on sm.id = se.material_id " +
            "left join user u on se.teacher_user_id = u.id " +
            "where sm.id = #{id}")
    StudentMaterialVO getByIdWithEvaluation(Long id);

    @Select("select sm.*, (case when se.id is null then 0 else 1 end) as evaluated, se.id as evaluation_id, se.score, se.content as evaluation_content, se.evaluation_time, se.teacher_user_id, u.real_name as teacher_real_name " +
            "from student_material sm " +
            "left join student_evaluation se on sm.id = se.material_id " +
            "left join user u on se.teacher_user_id = u.id " +
            "where sm.student_user_id = #{studentId} " +
            "order by sm.submit_time desc")
    List<StudentMaterialVO> getMaterialsByStudentId(Long studentId);

    /**
     * 根据ID查询
     * @param id
     * @return
     */
    @Select("select * from student_material where id = #{id}")
    StudentMaterial getById(Long id);

    /**
     * 根据ID删除
     * @param id
     */
    @Delete("delete from student_material where id = #{id}")
    void deleteById(Long id);

    /**
     * 更新
     * @param studentMaterial
     */
    void update(StudentMaterial studentMaterial);

    /**
     * 分页查询
     * @param studentMaterial
     * @return
     */
    Page<StudentMaterialVO> pageQuery(StudentMaterial studentMaterial);

    Page<StuMaterialPageVO> pageQueryForTeacher(@Param("dto") StuMatTeaSearchPageDTO dto, @Param("teacherId") Long teacherId);

    Page<StuMaterialPageVO> pageQueryForAdmin(@Param("dto") StuMatTeaSearchPageDTO dto);

    @Select("select count(*) from student_material")
    Integer countAll();

    @Select("select count(*) from student_material where material_type = #{type}")
    Integer countByType(@Param("type") Integer type);

    @Select("select date(submit_time) as day, count(*) as count from student_material where submit_time >= #{startTime} group by date(submit_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCount(@Param("startTime") java.time.LocalDateTime startTime);

    @Select("select date(submit_time) as day, count(*) as count from student_material where material_type = #{type} and submit_time >= #{startTime} group by date(submit_time) order by day")
    java.util.List<com.psqin.domain.vo.DailyCountVO> listDailyCountByType(@Param("type") Integer type, @Param("startTime") java.time.LocalDateTime startTime);

    @Select("select count(*) from student_material sm join ts_guidance tg on tg.student_user_id = sm.student_user_id where tg.teacher_user_id = #{teacherUserId}")
    Integer countByTeacherUserId(@Param("teacherUserId") Long teacherUserId);

    @Select("select count(*) " +
            "from student_material sm " +
            "join ts_guidance tg on tg.student_user_id = sm.student_user_id " +
            "left join student_evaluation se on se.material_id = sm.id " +
            "where tg.teacher_user_id = #{teacherUserId} and se.id is null")
    Integer countUnevaluatedByTeacherUserId(@Param("teacherUserId") Long teacherUserId);

    @Select("select count(*) " +
            "from student_material sm " +
            "join ts_guidance tg on tg.student_user_id = sm.student_user_id " +
            "join student_evaluation se on se.material_id = sm.id " +
            "where tg.teacher_user_id = #{teacherUserId} and se.teacher_user_id = #{teacherUserId}")
    Integer countEvaluatedByTeacherUserId(@Param("teacherUserId") Long teacherUserId);
}
