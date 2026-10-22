package com.psqin.mapper;

import com.github.pagehelper.Page;
import com.psqin.domain.dto.AdminStudentSearchDTO;
import com.psqin.domain.dto.StudentSearchDTO;
import com.psqin.domain.entity.Students;
import com.psqin.domain.vo.StudentVO;
import com.psqin.domain.vo.StudentsPageVO;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Update;

import java.util.List;

/**
 *
 */
@Mapper
public interface StudentMapper {

    @Insert("insert into students (user_id, student_no, university_id, college_id, major_id, class_id, entry_year) " +
            "values " +
            "(#{userId}, #{studentNo}, #{universityId}, #{collegeId}, #{majorId}, #{classId}, #{entryYear})")
    void insert(Students student);


    Page<StudentsPageVO> pageQuery(Students students);

    @Select("select * from students where user_id = #{userId}")
    Students getByUserId(Long userId);

    @Select("select * from students where id = #{id}")
    Students getById(Long id);

    /**
     * 根据用户ID查询学生详细信息
     * @param userId
     * @return
     */
    @Select("select s.*, u.name as university_name, c.name as college_name, m.name as major_name, cl.name as class_name, " +
            "us.real_name, us.avatar, us.gender " +
            "from students s " +
            "left join universities u on s.university_id = u.id " +
            "left join sys_dept c on s.college_id = c.id " +
            "left join sys_dept m on s.major_id = m.id " +
            "left join sys_dept cl on s.class_id = cl.id " +
            "left join user us on s.user_id = us.id " +
            "where s.user_id = #{userId}")
    StudentVO getStudentInfoByUserId(Long userId);

    Page<StudentVO> pageQueryAdmin(AdminStudentSearchDTO adminStudentSearchDTO);

    void update(Students student);

    void deleteById(@Param("id") Long id);

    List<Students> listByUserIds(@Param("userIds") List<Long> userIds);

    void updateBindStatusByUserIds(@Param("userIds") List<Long> userIds, @Param("bindStatus") Integer bindStatus);

    @Update("update students set bind_status = 0 where user_id in (select student_user_id from ts_guidance where teacher_user_id = #{teacherUserId})")
    void unbindByTeacherUserId(@Param("teacherUserId") Long teacherUserId);

    /**
     * 将指定导师的所有学生的绑定状态设置为未绑定
     * @param teacherId
     */
    @Update("update students set bind_status = 0 where id in (select ts_guidance.student_user_id from ts_guidance where student_user_id = #{teacherId})")
    void unbindByTeacherId(Long teacherId);

    StudentVO getStudentInfoByStudentId(@Param("id") Long id);

    @Select("select count(*) from students")
    Integer countAll();

    @Select("select u.name as name, count(*) as count from students s join universities u on s.university_id = u.id group by s.university_id order by count desc")
    java.util.List<com.psqin.domain.vo.NameCountVO> listCountByUniversity();
}
